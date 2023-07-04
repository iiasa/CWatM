Create webpages for CWatM
-------------------------

Create empty repro
------------------

git switch --orphan pages
git commit --allow-empty -m "Initial empty webpages"
git push -u origin pages



Copy files to folder
--------------------

git status

git add --all
git commit -m "webpages"

Github - settings
-----------------

"Code and automation" section of the sidebar, click Pages
"Build and deployment", under "Source", select Deploy from a branch -> save

Custom domain change to cwatm.iiasa.ac.at

Change documention .rst
-----------------------

in https://github.com/iiasa/CWatM/tree/develop/Toolkit/documentation
change rst files in your drive

run runMake.bat (see Readme.docx in this folder)

new build html are in: _build/html

commit and push to github

Copy to branch pages
--------------------

copy all the stuff from _build/html to branch pages (checkout pages to local drive, copy _build/html, commit and push back)

