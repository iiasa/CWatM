# -------------------------------------------------------------------------
# Name:        Reservoir transfers
# Purpose:     Water transfers between reservoirs (and from/to outside) with the rules 1-6 of the
#              Excel sheet Reservoir_transfers: check at the start, transfer in each routing substep
#
# Author:      PB, DF
# Created:     06/11/2026 (from lakes_reservoirs.py)
# CWatM is licensed under GNU GENERAL PUBLIC LICENSE Version 3.
# -------------------------------------------------------------------------

from cwatm.management_modules.data_handling import *


class reservoir_transfers(object):
    """
    Water transfers between reservoirs

    The Excel sheet Reservoir_transfers (read in initcondition.py) gives for each transfer the rule,
    the giving and the receiving reservoir (0 = outside), a limit and 366 daily values.
    Transfers only work between reservoirs (not lakes or wetlands, type 1 and 6).
    A receiving reservoir which is not in the model (e.g. outside the mask map) counts as 0 (outside),
    a transfer with a giving reservoir which is not in the model is not used.

    Rules:
    1 - fraction of live storage (values <= 1)
    2 - fraction of live storage (values <= 1), limit: minimum reservoir volume which is preserved
    3 - m3 of storage volume, limit: minimum reservoir volume which is preserved
    4 - fraction of outflow (values <= 1), limit: minimum discharge [m3/s]
    5 - fraction of outflow (values <= 1), limit: 'minimum discharge,maximum discharge' [m3/s]
    6 - fixed outflow [m3/s], limit: minimum discharge [m3/s]

    **Global variables**
    ===================================  ==========    ======================================================================  =====
    Variable [self.var]                  Type          Description                                                             Unit 
    ===================================  ==========    ======================================================================  =====
    reservoir_transfers                  Array         [['Giving reservoir'][i], ['Receiving reservoir'][i], ['Fraction of li  array
    reservoir_transfers_option           Flag          True if reservoir_transfers = True (Excel sheet Reservoir_transfers)    bool 
    reservoir_transfers_fixyear          Number        fixLakesResYear if dynamicLakesRes = False (else None)                  year 
    reservoir_transfers_net_M3C          Array         Net transfer from one point to the other                                m3   
    reservoir_transfers_net_M3           Array         net reservoir transfers, after exports, transfers, and imports          m3   
    reservoir_transfers_in_M3C           Array         Transfer - what goes into the receiving reservoir                       m3   
    reservoir_transfers_in_M3            Array         water received into reservoirs                                          m3   
    reservoir_transfers_out_M3C          Array         Transfer - what goes out from the giving reservoir                      m3   
    reservoir_transfers_out_M3           Array         water given from reservoirs                                             m3   
    waterBodyID_C                        Array         ID of the waterbody - compressed                                        --   
    waterBodyTypC                        Array         water body types 3 reservoirs and lakes (used as reservoirs but before  --   
    resYearC                             Array         Compressed map of resYear                                               --   
    resVolumeC                           Array         compressed map of reservoir volume                                      Mm3  
    reservoirStorageM3C                  Array         Initial reservoir fill (fraction of total storage, [-]) (AI)            --   
    compress_LR                          Array         boolean map as mask map for compressing lake/reservoir                  --   
    decompress_LR                        Array         boolean map as mask map for decompressing lake/reservoir                --   
    dtRouting                            Array         number of seconds per routing timestep                                  s    
    noRoutingSteps                       Number        Number of routing step - how often the subroutine is run during a day   --   
    ===================================  ==========    ======================================================================  =====

    **Functions**
    """

    def __init__(self, model):
        self.var = model.var
        self.model = model

    def initial(self):
        """
        Initial part of the reservoir transfers: daily sums, option, year and check of the transfers
        (called at the end of lakes_reservoirs.initial_reservoirs, after the water body types are final)
        """
        # daily sums of the transfers (compressed: sum of the routing substeps, full map: value of the day)
        self.var.reservoir_transfers_net_M3C = np.compress(self.var.compress_LR, globals.inZero.copy())
        self.var.reservoir_transfers_net_M3 = globals.inZero.copy()
        self.var.reservoir_transfers_in_M3C = np.compress(self.var.compress_LR, globals.inZero.copy())
        self.var.reservoir_transfers_in_M3 = globals.inZero.copy()
        self.var.reservoir_transfers_out_M3C = np.compress(self.var.compress_LR, globals.inZero.copy())
        self.var.reservoir_transfers_out_M3 = globals.inZero.copy()

        # option checked once, used in each routing substep
        self.var.reservoir_transfers_option = checkOption('reservoir_transfers', True)
        if not self.var.reservoir_transfers_option:
            return

        # year for the construction check: the year of the day or a fixed year (loaded once)
        self.var.reservoir_transfers_fixyear = None
        if not returnBool('dynamicLakesRes'):
            self.var.reservoir_transfers_fixyear = loadmap('fixLakesResYear')

        #  check if transfer has a valid receiver or giver
        # 0 = from/to outside; otherwise the reservoir has to be a lake/reservoir in the model
        ids = set(self.var.waterBodyID_C.tolist()) | {0}
        valid = []
        for trans in self.var.reservoir_transfers:
            rule, giver, receiver = trans[0], trans[1], trans[2]
            name = "Reservoir transfer " + str(giver) + " -> " + str(receiver) + " (rule " + str(rule) + ")"

            # giving reservoir not in the model (e.g. outside the mask map) -> transfer is not used
            if not (giver in ids):
                print_cwatm_warning(name + " is not used:\ngiving reservoir No: " + str(giver) + " is not a lake/reservoir in the model\n")
                continue
            # receiving reservoir not in the model (e.g. outside the mask map) -> water leaves the model (receiver = 0)
            if not (receiver in ids):
                print_cwatm_warning(name + ": receiving reservoir No: " + str(receiver) + " is not a lake/reservoir in the model (e.g. outside the mask map)\nthe water is transferred to outside (receiving reservoir = 0)\n")
                receiver = 0
                trans = [rule, giver, receiver] + list(trans[3:])
            # wrong settings -> error
            if giver == 0 and receiver == 0:
                raise CWATMError(name + ": giving and receiving reservoir are both 0 (outside)\n")
            if not (rule in (1, 2, 3, 4, 5, 6)):
                raise CWATMError(name + ": rule has to be 1 to 6\n")
            if giver == 0 and rule in (2, 4, 5):
                raise CWATMError(name + ": rules 2, 4 and 5 need a giving reservoir (storage or outflow), not 0 (outside)\n")
            if rule == 5 and len(str(trans[3]).split(",")) != 2:
                raise CWATMError(name + ": rule 5 needs the limit as 'minimum discharge,maximum discharge' e.g. 1.0,10.0\n")
            # transfers work on reservoir storage/outflow: lakes and wetlands (type 1, 6) cannot give or receive
            for rid in (giver, receiver):
                if rid > 0 and self.var.waterBodyTypC[self.var.waterBodyID_C == rid][0] in (1, 6):
                    raise CWATMError(name + ": water body No: " + str(rid) + " is a lake or wetland (type 1 or 6) - transfers only between reservoirs\n")

            valid.append(trans)
        self.var.reservoir_transfers = valid

    def route(self, qResOutM3DtC):
        """
        Transfer water between reservoirs in one routing substep

        Send storage between reservoirs using the Excel sheet Reservoir_transfers within cwatm_settings.xlsx.
        Using the waterBodyIDs defined in the settings, designate the Giver, the Receiver, and the daily
        fraction of live storage the Giver sends to the Receiver.
        If the Receiver is already at capacity, the Giver does not send any storage.
        Reservoirs can only send to one reservoir. Reservoirs can receive from several reservoirs.

        :param qResOutM3DtC: reservoir outflow [m3] per routing substep
        :return: qResOutM3DtC - reservoir outflow [m3] after the transfers (rules 4-6 split the outflow)
        """
        inZero_C = np.zeros(self.var.waterBodyID_C.size)
        # year for the construction check
        if self.var.reservoir_transfers_fixyear is None:
            year = dateVar['currDate'].year
        else:
            year = self.var.reservoir_transfers_fixyear

        for transfer in self.var.reservoir_transfers:

            if transfer[1] > 0:
                # using Giving reservoir ID from Excel - if this is 0 it is from outside
                giver = np.where(self.var.waterBodyID_C == transfer[1])[0][0]
                giver_already_constructed = self.var.resYearC[giver] <= year
            else:
                giver_already_constructed = True

            if transfer[2] > 0:
                # using the Receiving reservoir from Excel
                receiver = np.where(self.var.waterBodyID_C == transfer[2])[0][0]
                receiver_already_constructed = self.var.resYearC[receiver] <= year
            else:
                receiver_already_constructed = True


            if receiver_already_constructed and giver_already_constructed:
                # if giving and receiving station already exist (is build before the year which is modelled)
                if (transfer[2] == 0) or ((self.var.waterBodyTypC[receiver] > 3) & (self.var.waterBodyTypC[receiver] < 6)):
                    # if receiver is outside OR the receiving is a reservoir type > 3
                    reservoir_unused_receiver = 10e12
                else:
                    # check if there is space for the water in the receiving reservoir
                    reservoir_unused_receiver = self.var.resVolumeC[receiver] - self.var.reservoirStorageM3C[receiver]

                if transfer[1] > 0:
                    reservoir_storage_giver = self.var.reservoirStorageM3C[giver]
                else:
                    # In this case, the fraction refers to the fraction of the receiver,
                    # as the giver is infinite
                    reservoir_storage_giver = self.var.resVolumeC[receiver]



                # --- Rulesets -------------------
                # use different rulesets:
                limit =  transfer[3]
                # Rule 1: Fraction of live storage (values <= 1) (default)
                if transfer[0] == 1:
                    reservoir_transfer_actual = reservoir_storage_giver * transfer[4][dateVar['doy'] - 1] / self.var.noRoutingSteps

                # Rule 2: Fraction of live storage (values <= 1) e, LIMIT: miminum reservoir volume which should be preserved
                if transfer[0] == 2:
                    reservoir_transfer_actual = reservoir_storage_giver * transfer[4][dateVar['doy'] - 1] / self.var.noRoutingSteps
                    if (self.var.reservoirStorageM3C[giver] - reservoir_transfer_actual) < limit:
                        reservoir_transfer_actual = np.maximum(0, self.var.reservoirStorageM3C[giver] - limit)

                # Rule 3: m3 of storage volume, LIMIT: miminum reservoir volume which should be preserved
                if transfer[0] == 3:
                    reservoir_transfer_actual = transfer[4][dateVar['doy'] - 1] / self.var.noRoutingSteps
                    # the minimum volume only applies to a giving reservoir (not from outside)
                    if transfer[1] > 0 and (self.var.reservoirStorageM3C[giver] - reservoir_transfer_actual) < limit:
                        reservoir_transfer_actual = np.maximum(0, self.var.reservoirStorageM3C[giver] - limit)


                # if rule is based on volume:
                if transfer[0] < 4:
                    reservoir_transfer_actual = np.maximum(0., np.minimum(reservoir_unused_receiver * 0.95, reservoir_transfer_actual))

                # --- Outflow -------------------------------
                # Outflow based rules
                # Rule 4: Fraction of outflow (values <= 1) Limit: minimum discharge
                if transfer[0] == 4:
                    limit = limit * self.var.dtRouting
                    if transfer[1] == 0:  # giver is outside
                        limit = 0
                    # to get from m3/s to m3 of the substep routing poeriod
                    qnew = qResOutM3DtC[giver] * (1 - transfer[4][dateVar['doy'] - 1])  # [m3]
                    if qnew < limit:
                        qnew = np.minimum(qResOutM3DtC[giver], limit)
                    reservoir_transfer_actual = qResOutM3DtC[giver] - qnew
                    qResOutM3DtC[giver] = qnew

                # Rule 5: Fraction of outflow (values <= 1)
                # Limit: minimum discharge, maximum discharge to receiving reservoir [m3/s]
                if transfer[0] == 5:
                    limit= transfer[3].split(",")
                    limit1 = float(limit[0]) * self.var.dtRouting  # m3/s to m3 in the routing substep period
                    limit2 = float(limit[1]) * self.var.dtRouting
                    if transfer[1] == 0:  # giver is outside
                        limit1 = 0
                    # to get to m3 from m3/s but including routing steps
                    #mult = self.var.DtSec / self.var.noRoutingSteps
                    qnew = qResOutM3DtC[giver]  * (1 - transfer[4][dateVar['doy'] - 1]) # in m3
                    if qnew < limit1:
                        qnew = np.minimum(qResOutM3DtC[giver] , limit1)
                    if (qResOutM3DtC[giver] - qnew) < limit2:
                        reservoir_transfer_actual = qResOutM3DtC[giver] - qnew
                    else:
                        reservoir_transfer_actual = limit2
                        qnew = qResOutM3DtC[giver] - reservoir_transfer_actual
                    qResOutM3DtC[giver] = qnew


                # Rule 6: Fix of outflow, [m3/s]
                # Limit: minimum discharge [m3/s]
                if transfer[0] == 6:
                    reservoir_transfer_actual = transfer[4][dateVar['doy'] - 1]  * self.var.dtRouting
                    # from m3/s to m3
                    if transfer[1] > 0:
                        # split from the outflow of the giving reservoir, but keep the minimum discharge
                        limit = limit * self.var.dtRouting
                        qnew = qResOutM3DtC[giver] - reservoir_transfer_actual
                        if qnew < limit:
                            qnew = np.minimum(qResOutM3DtC[giver], limit)
                        reservoir_transfer_actual = qResOutM3DtC[giver] - qnew
                        qResOutM3DtC[giver] = qnew


                # -----------------------------------------
                if transfer[1] > 0:
                    # There is a giver, not the ocean
                    inZero_C[giver] += -reservoir_transfer_actual
                    self.var.reservoir_transfers_out_M3C[giver] += reservoir_transfer_actual

                    if transfer[0] < 4:
                        # if given from storage than (not if split from outflow)
                        self.var.reservoirStorageM3C[giver] = self.var.reservoirStorageM3C[giver] - reservoir_transfer_actual

                if transfer[2] > 0:  # There is a receiver, not the ocean
                    inZero_C[receiver] += reservoir_transfer_actual  # receiver
                    self.var.reservoirStorageM3C[receiver] = self.var.reservoirStorageM3C[receiver] + reservoir_transfer_actual
                    self.var.reservoir_transfers_in_M3C[receiver] += reservoir_transfer_actual

        self.var.reservoir_transfers_net_M3C += inZero_C
        return qResOutM3DtC

    def daily_output(self):
        """
        Last routing substep of the day: daily sums to the full maps, then the sums start again at 0
        (the transfers only add to the compressed sums in each substep)
        """
        np.put(self.var.reservoir_transfers_net_M3, self.var.decompress_LR, self.var.reservoir_transfers_net_M3C)
        np.put(self.var.reservoir_transfers_out_M3, self.var.decompress_LR, self.var.reservoir_transfers_out_M3C)
        np.put(self.var.reservoir_transfers_in_M3, self.var.decompress_LR, self.var.reservoir_transfers_in_M3C)
        self.var.reservoir_transfers_net_M3C.fill(0.)
        self.var.reservoir_transfers_out_M3C.fill(0.)
        self.var.reservoir_transfers_in_M3C.fill(0.)
