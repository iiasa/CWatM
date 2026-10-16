# Purpose: grid of the CWatM - MODFLOW coupling: ModFlow domain, the index pairs of overlapping CWatM / ModFlow cells
# (with the area of each overlap) and the conversion of maps between the CWatM and the ModFlow grid.
# Reading and writing of files: management_modules/data_modflow.py
import numpy as np
import rasterio.warp
from rasterio.crs import CRS

from cwatm.management_modules.data_handling import *
from cwatm.management_modules.data_modflow import (raster_crs, read_modflow_basin, read_modflow_tif, on_modflow_grid,
                                                   write_modflow_netcdf, read_modflow_netcdf)


def is_float(s):
    """True if the string s can be converted to float"""
    try:
        float(s)
        return True
    except ValueError:
        return False


def decompress(map, nanvalue=None):
    """
    Decompress a CWatM map from 1D to 2D with missing values (nan values replaced by nanvalue if given)
    """
    dmap = maskinfo['maskall'].copy()
    dmap[~maskinfo['maskflat']] = map[:]
    if nanvalue is not None:
        dmap.data[np.isnan(dmap.data)] = nanvalue
    return dmap.data


def clip_halfplane(poly, axis, value, sign):
    """
    Clip convex polygons (N, M, 2) - padded by repeating the last vertex - to sign * (coordinate[axis] - value) >= 0
    (Sutherland-Hodgman, vectorised; value: one per polygon). Returns polygons (N, K, 2) padded the same way;
    an empty polygon is all zeros (area 0)
    """
    n, m, _ = poly.shape
    value = np.asarray(value, dtype=np.float64)[:, None]
    e = poly
    s = np.roll(poly, 1, axis=1)
    de = sign * (e[..., axis] - value)
    ds = sign * (s[..., axis] - value)
    ine, ins = de >= 0, ds >= 0
    cross = ine != ins
    # intersection of the edge S -> E with the line (only where it crosses: no division by 0)
    t = np.zeros_like(de)
    np.divide(ds, ds - de, out=t, where=cross)
    inter = s + t[..., None] * (e - s)
    inter[..., axis] = np.where(cross, value, inter[..., axis])
    # each edge S -> E gives: the intersection (if it crosses), then E (if E is inside)
    pts = np.stack([inter, e], axis=2).reshape(n, 2 * m, 2)
    valid = np.stack([cross, ine], axis=2).reshape(n, 2 * m)
    count = valid.sum(axis=1)
    k = max(int(count.max()), 1) if n else 1
    pos = np.cumsum(valid, axis=1) - 1
    rows = np.broadcast_to(np.arange(n)[:, None], valid.shape)
    out = np.zeros((n, k, 2))
    out[rows[valid], pos[valid]] = pts[valid]
    # padding: repeat the last vertex
    last = out[np.arange(n), np.maximum(count - 1, 0)]
    pad = np.arange(k)[None, :] >= count[:, None]
    out[pad] = np.broadcast_to(last[:, None, :], out.shape)[pad]
    return out


def polygon_area(poly):
    """Area of polygons (N, M, 2) (shoelace formula)"""
    x, y = poly[..., 0], poly[..., 1]
    return 0.5 * np.abs(np.sum(x * np.roll(y, -1, axis=1) - np.roll(x, -1, axis=1) * y, axis=1))


def overlap_table(mf_transform, mf_shape, mf_crs, cw_west, cw_north, cw_cell, cw_shape, cw_crs):
    """
    Pairs of overlapping ModFlow / CWatM cells from the two grid definitions (exact polygon overlap)

    The corners of the ModFlow cells are transformed to the CRS of CWatM (if different), each ModFlow cell is then a
    quadrilateral, which is clipped to the CWatM cells it touches. The area of a pair is the share of the ModFlow cell
    in the CWatM cell times the ModFlow cell area (m2). Pairs outside the CWatM grid are left out.
    Returns modflow_y, modflow_x, cwatm_y, cwatm_x, area
    """
    nrow, ncol = mf_shape
    xs = mf_transform.c + np.arange(ncol + 1) * mf_transform.a
    ys = mf_transform.f + np.arange(nrow + 1) * mf_transform.e
    X, Y = np.meshgrid(xs, ys)
    if CRS.from_user_input(mf_crs) != CRS.from_user_input(cw_crs):
        tx, ty = rasterio.warp.transform(mf_crs, cw_crs, X.ravel(), Y.ravel())
        X, Y = np.asarray(tx).reshape(X.shape), np.asarray(ty).reshape(Y.shape)
    # CWatM grid units: column u, row v (each CWatM cell is a unit square)
    U = (X - cw_west) / cw_cell
    V = (cw_north - Y) / cw_cell

    my, mx = np.divmod(np.arange(nrow * ncol), ncol)
    corners = [(my, mx), (my, mx + 1), (my + 1, mx + 1), (my + 1, mx)]
    quad = np.stack([np.stack([U[i, j], V[i, j]], -1) for i, j in corners], axis=1)
    quad_area = polygon_area(quad)
    mf_area = abs(mf_transform.a * mf_transform.e)

    # CWatM cells touched by the bounding box of each ModFlow cell
    u0 = np.floor(quad[..., 0].min(1)).astype(np.int64)
    u1 = np.ceil(quad[..., 0].max(1)).astype(np.int64)
    v0 = np.floor(quad[..., 1].min(1)).astype(np.int64)
    v1 = np.ceil(quad[..., 1].max(1)).astype(np.int64)
    out = [], [], [], [], []

    def add(sel, cv, cu, area):
        keep = (area > 0) & (cu >= 0) & (cu < cw_shape[1]) & (cv >= 0) & (cv < cw_shape[0])
        for lst, a in zip(out, (my[sel], mx[sel], cv, cu, area)):
            lst.append(a[keep])

    # ModFlow cells inside one CWatM cell: the whole cell area
    one = (u1 - u0 == 1) & (v1 - v0 == 1)
    sel = np.flatnonzero(one)
    add(sel, v0[sel], u0[sel], np.full(len(sel), mf_area))

    # the others: clipped to each CWatM column, then to each row of it
    rest = np.flatnonzero(~one)
    for du in range(int((u1 - u0)[rest].max()) if len(rest) else 0):
        sel = rest[u0[rest] + du < u1[rest]]
        cu = u0[sel] + du
        strip = clip_halfplane(clip_halfplane(quad[sel], 0, cu, 1), 0, cu + 1, -1)
        for dv in range(int((v1 - v0)[sel].max())):
            k = np.flatnonzero(v0[sel] + dv < v1[sel])
            cv = v0[sel][k] + dv
            p = clip_halfplane(clip_halfplane(strip[k], 1, cv, 1), 1, cv + 1, -1)
            add(sel[k], cv, cu[k], polygon_area(p) / quad_area[sel[k]] * mf_area)
    return tuple(np.concatenate(a) for a in out)


def cwatm_crs():
    """
    CRS of the CWatM grid: setting cwatm_crs (e.g. EPSG:4326), else the CRS of the MaskMap file, else lat/lon
    (EPSG:4326) if the grid has lat/lon coordinates (e.g. a PCRaster .map without CRS)
    """
    if 'cwatm_crs' in binding:
        return CRS.from_user_input(cbinding('cwatm_crs'))
    crs = raster_crs(cbinding('MaskMap'))  # None: MaskMap as coordinates or a file without CRS
    if crs is not None:
        return crs
    west, north, cell = maskmapAttr['x'], maskmapAttr['y'], maskmapAttr['cell']
    east, south = west + maskmapAttr['col'] * cell, north - maskmapAttr['row'] * cell
    if cell < 1 and -180 <= west < east <= 360 and -90 <= south < north <= 90:
        return CRS.from_epsg(4326)
    msg = "Error 147: the CRS of the CWatM grid (MaskMap) is not known - set e.g. cwatm_crs = EPSG:3035 in\n"
    msg += "[GROUNDWATER_MODFLOW] (needed to compute the overlap of CWatM and ModFlow cells)\n"
    raise CWATMError(msg)


class ModflowGrid:
    """
    ModFlow grid and the conversion of maps between CWatM (1D compressed) and ModFlow (2D: nrow, ncol)

    Settings: modflow_basin (tif of the active ModFlow cells with CRS, defines the ModFlow grid). The pairs of
    overlapping CWatM / ModFlow cells are computed from the two grids (CRS of CWatM: see cwatm_crs) - before
    2026-10-13 they could also be read from .npy files (modflow_indices_from_files, cwatm_modflow_indices).

    Attributes
    ----------
    basin : 2D bool array of the active ModFlow cells
    domain : dict nrow, ncol, rowsize, colsize, west, east, north, south (also the global domain of data_handling)
    cell_area : area of one ModFlow cell (m2)
    """

    def __init__(self, cellArea):
        """cellArea: CWatM cell area (1D, m2) - the overlap areas are corrected to add up to it"""
        # active ModFlow cells as 2-dimensional array (nrows, ncols), grid and CRS
        self.basin, transform, modflow_crs = read_modflow_basin(cbinding('modflow_basin'))
        height, width = self.basin.shape
        self.domain = {
            'rowsize': abs(transform.e),
            'colsize': abs(transform.a),
            'nrow': int(height),
            'ncol': int(width),
            'west': transform.c,
            'east': transform.c + (width - 1) * abs(transform.a),
            'north': transform.f,
            'south': transform.f - (height - 1) * abs(transform.e)
        }
        # global domain: also used in data_handling to write netcdf maps at ModFlow resolution
        domain.update(self.domain)
        domain['crs'] = modflow_crs
        self.transform, self.crs = transform, modflow_crs
        self.nrow, self.ncol = self.domain['nrow'], self.domain['ncol']
        self.cell_area = self.domain['rowsize'] * self.domain['colsize']  # in m2

        # index pairs of overlapping CWatM / ModFlow cells (before 2026-10-13 optionally read from .npy files:
        # modflow_indices_from_files - no longer used)
        if 'modflow_indices_from_files' in binding and returnBool('modflow_indices_from_files'):
            print(CWATMWarning("Warning: modflow_indices_from_files is not used any more - the index pairs of CWatM "
                               "and ModFlow cells are computed from modflow_basin and MaskMap"))
        # ModFlow grid without CRS: same CRS as CWatM
        cw_crs = cwatm_crs()
        pairs = overlap_table(transform, self.basin.shape, cw_crs if modflow_crs is None else modflow_crs, maskmapAttr['x'],
                              maskmapAttr['y'], maskmapAttr['cell'], maskinfo['shape'], cw_crs)
        # only CWatM cells inside the mask (the others have no cell area); sorted by ModFlow cell, CWatM cell
        inmask = ~maskinfo['mask'][pairs[2], pairs[3]]
        self.modflow_y, self.modflow_x, self.cwatm_y, self.cwatm_x, area = (a[inmask] for a in pairs)
        order = np.lexsort((self.cwatm_y * maskinfo['shape'][1] + self.cwatm_x,
                            self.modflow_y * self.ncol + self.modflow_x))
        self.modflow_y, self.modflow_x, self.cwatm_y, self.cwatm_x, area = (
            a[order] for a in (self.modflow_y, self.modflow_x, self.cwatm_y, self.cwatm_x, area))
        self.modflow_index = np.array(self.modflow_y * self.ncol + self.modflow_x)
        self.cwatm_index = np.array(self.cwatm_y * maskinfo['shape'][1] + self.cwatm_x)

        # active ModFlow cells outside the CWatM mask get nothing from CWatM (Bhima: 4403 of 187611 at the border);
        # more than half of them outside: wrong grid or CRS
        covered = np.bincount(self.modflow_index, weights=area, minlength=self.nrow * self.ncol) > 0
        outside = np.count_nonzero(self.basin.ravel() & ~covered)
        if outside > 0.5 * np.count_nonzero(self.basin):
            msg = "Error 148: " + str(outside) + " of " + str(np.count_nonzero(self.basin))
            msg += " active ModFlow cells (modflow_basin) are not inside the CWatM mask\n"
            msg += "(check modflow_basin, MaskMap and the CRS of both: modflow_basin " + str(modflow_crs) + ")\n"
            raise CWATMError(msg)

        # area of each pair, corrected so that the pairs of a CWatM cell add up to its cell area
        cwatm_cell_area = decompress(cellArea, nanvalue=0)
        indices_cell_area = np.bincount(self.cwatm_index, weights=area, minlength=cwatm_cell_area.size)
        with np.errstate(divide='ignore', invalid='ignore'):
            area_correction = (cwatm_cell_area / indices_cell_area)[self.cwatm_index]
        self.area = area * area_correction
        # for each ModFlow cell the pair with the largest overlap (from_cwatm_cells); same area: the last pair as before
        order = np.lexsort((np.nan_to_num(self.area), self.modflow_index))
        self.largest_pair = order[np.append(self.modflow_index[order][1:] != self.modflow_index[order][:-1], True)]

        # for each MODFLOW step (to_modflow, to_cwatm): only the pairs of active ModFlow cells and CWatM cells in the
        # mask (the others are not used by MODFLOW or add 0, Bhima: half of them), with the CWatM cell as index of
        # the compressed (1D) CWatM map - no conversion to 2D CWatM maps
        compressed = np.full(maskinfo['shapeflat'][0], -1, dtype=np.int64)
        compressed[~maskinfo['maskflat']] = np.arange(maskinfo['mapC'][0])
        inbasin = self.basin.ravel()[self.modflow_index] & (compressed[self.cwatm_index] >= 0)
        self.modflow_index_basin = self.modflow_index[inbasin]
        self.cwatm_compressed_basin = compressed[self.cwatm_index[inbasin]]
        self.area_basin = self.area[inbasin]
        self.cwatm_cell_area = np.asarray(cellArea, dtype=np.float64)  # in m2, 1D compressed
        # area of each CWatM cell covered by active ModFlow cells (border cells: less than the cell area)
        self.covered_area = np.bincount(self.cwatm_compressed_basin, weights=self.area_basin,
                                        minlength=maskinfo['mapC'][0])
        # area of each ModFlow cell inside the CWatM mask (cells partly outside the mask: less than the cell area)
        self.modflow_covered_all = np.bincount(self.modflow_index, weights=self.area, minlength=self.nrow * self.ncol)
        self.modflow_covered = np.bincount(self.modflow_index_basin, weights=self.area_basin,
                                           minlength=self.nrow * self.ncol)

    def read_tif(self, name):
        """map at ModFlow resolution (tif of the settings key name, same grid as modflow_basin) as float32"""
        return read_modflow_tif(cbinding(name))

    def write_netcdf(self, filename, name, data, units, long_name):
        """
        Map at ModFlow resolution (2D, nrow x ncol, or 3D with layers, nlay x nrow x ncol) as netCDF: float64 (exact
        values, e.g. the head for a restart), x / y of the cell centres, CRS of modflow_basin, nan outside the basin
        """
        write_modflow_netcdf(filename, name, data, units, long_name, self.transform, self.crs)

    def read_map(self, filename, nlay=1, variable=None):
        """
        Maps of nlay layers at ModFlow resolution (nlay, nrow, ncol) from a netCDF file (the variable with 3
        dimensions layer, row, col - or 2 dimensions row, col for one layer), values as they are stored (no mask).
        variable: name of the netCDF variable (default: the last variable with 2 or 3 dimensions). Before 2026-10-13
        also a .npy file
        """
        return read_modflow_netcdf(filename, nlay, self.nrow, self.ncol, variable)

    def to_modflow(self, variable, nanvalue=None, all_cells=False):
        """
        CWatM map (1D compressed) -> ModFlow map (2D, float64), area-weighted mean of the CWatM cells over the part
        of the ModFlow cell inside the CWatM mask (flow L/T or depth) - ModFlow cells outside the mask: 0
        nanvalue: value for nan in the CWatM map
        all_cells: also the ModFlow cells outside the basin (e.g. output maps at the start), else only active
        ModFlow cells (MODFLOW steps: faster, the other cells are 0)
        """
        if all_cells:
            variable = decompress(variable, nanvalue)
            total = np.bincount(self.modflow_index, variable.ravel()[self.cwatm_index] * self.area,
                                minlength=self.nrow * self.ncol)
            with np.errstate(divide='ignore', invalid='ignore'):
                result = np.where(self.modflow_covered_all > 0, total / self.modflow_covered_all, 0)
            return result.reshape((self.nrow, self.ncol)).astype(variable.dtype)
        variable = np.asarray(variable, dtype=np.float64)
        if nanvalue is not None:
            variable = np.where(np.isnan(variable), nanvalue, variable)
        total = np.bincount(self.modflow_index_basin, variable[self.cwatm_compressed_basin] * self.area_basin,
                            minlength=self.nrow * self.ncol)
        with np.errstate(divide='ignore', invalid='ignore'):
            return np.where(self.modflow_covered > 0, total / self.modflow_covered, 0).reshape((self.nrow, self.ncol))

    def to_cwatm(self, variable, mean=False):
        """
        ModFlow map (2D) -> CWatM map (1D compressed), area-weighted (only active ModFlow cells)
        mean = False: divided by the CWatM cell area (flows, storage: volume is kept)
        mean = True: mean of the active ModFlow cells (head, elevation, permeability) - CWatM cells without an
        active ModFlow cell: 0
        """
        values = variable.ravel()[self.modflow_index_basin]
        assert not (np.isnan(values).any())
        total = np.bincount(self.cwatm_compressed_basin, weights=values * self.area_basin,
                            minlength=maskinfo['mapC'][0])
        if mean:
            with np.errstate(divide='ignore', invalid='ignore'):
                return np.where(self.covered_area > 0, total / self.covered_area, 0).astype(variable.dtype)
        return (total / self.cwatm_cell_area).astype(variable.dtype)

    def fraction_to_cwatm(self, variable):
        """fraction of each CWatM cell covered by ModFlow cells with variable > 0 (1D compressed)"""
        return self.to_cwatm(np.where(variable > 0, 1, variable).astype(variable.dtype))

    def kept_to_cwatm(self, variable, kept):
        """
        Part of a CWatM map (1D compressed, depth) which the overlap pairs give to the active ModFlow cells with kept
        (2D bool), as depth over each CWatM cell (1D compressed): the share of each CWatM cell itself - to_modflow
        mixes the CWatM cells of a ModFlow cell
        """
        weights = np.nan_to_num(np.asarray(variable, dtype=np.float64))[self.cwatm_compressed_basin] * self.area_basin
        weights = weights * kept.ravel()[self.modflow_index_basin]
        return np.bincount(self.cwatm_compressed_basin, weights=weights,
                           minlength=maskinfo['mapC'][0]) / self.cwatm_cell_area

    def from_cwatm_cells(self, name, fill, factor=1):
        """
        Property on the ModFlow grid (one layer: 1, nrow, ncol): one value in the settings file, or a map at CWatM
        resolution (each ModFlow cell gets the value of the CWatM cell with the largest overlap - before 2026-10-11
        the last pair, i.e. the CWatM cell with the highest row / column; nan, 0, negative and masked cells: fill,
        fill = None: kept).
        factor: unit conversion (e.g. permeability m/s -> m/day)
        """
        value = cbinding(name)
        if is_float(value):
            return np.full((1, self.nrow, self.ncol), factor * float(value), dtype=np.float32)
        p1 = maskinfo['maskall'].copy()
        p1[~maskinfo['maskflat']] = loadmap(name)[:]
        p1 = p1.reshape(maskinfo['shape'])
        p1[p1.mask] = -9999
        values = np.zeros((1, self.nrow, self.ncol))
        pair = self.largest_pair
        values[0, self.modflow_y[pair], self.modflow_x[pair]] = p1.data[self.cwatm_y[pair], self.cwatm_x[pair]]
        if fill is not None:
            values[np.isnan(values) | (values <= 0)] = fill
        return values * factor

    def on_modflow_grid(self, filename):
        """True if filename is a raster with the ModFlow grid (same size and position as modflow_basin)"""
        return on_modflow_grid(filename, (self.nrow, self.ncol), self.transform)

    def layer_key(self, name, n):
        """
        Settings key of layer n (1, 2, ...): <name><n>, for layer 1 also <name> (settings files before 2026-10);
        None if missing
        """
        if name + str(n) in binding:
            return name + str(n)
        if n == 1 and name in binding:
            return name
        return None

    def property_map(self, key, fill=None, factor=1):
        """
        One layer (nrow, ncol) from a settings key: a value, a raster at ModFlow resolution (same grid as
        modflow_basin, read as float32) or a map at CWatM resolution (see from_cwatm_cells)
        fill: value for nan, 0 and negative values (None: kept). factor: unit conversion (e.g. m/s -> m/day)
        """
        value = cbinding(key)
        if not is_float(value) and self.on_modflow_grid(value):
            layer = self.read_tif(key)
            if fill is not None:
                layer[np.isnan(layer) | (layer <= 0)] = fill
            return layer * factor
        return self.from_cwatm_cells(key, fill, factor)[0]

    def layer_property(self, name, nlay, fill=None, factor=1, default=None):
        """
        Property of each layer on the ModFlow grid (nlay, nrow, ncol) from the settings keys <name>1 ... <name><nlay>
        (layer 1 also <name>), each a value or a map (see property_map).
        default: array (nlay, nrow, ncol) used for a missing key; None: a missing key is an error
        """
        layers = []
        for n in range(1, nlay + 1):
            key = self.layer_key(name, n)
            if key is not None:
                layers.append(self.property_map(key, fill, factor))
            elif default is not None:
                layers.append(default[n - 1])
            else:
                msg = "Error 150: " + name + str(n) + " is missing in the settings file - with nlay = " + str(nlay)
                msg += " each layer needs a value or map: "
                msg += ", ".join(name + str(i) for i in range(1, nlay + 1)) + "\n"
                raise CWATMError(msg)
        return np.stack(layers)
