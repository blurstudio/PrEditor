
function configure_preditor = (
    local pysite = python.import "site"
    local preditor_install = getFilenamePath(getSourceFileName())
    -- TODO: Figure out how to point to the preditor venv
    pysite.addsitedir @"C:\blur\lib\py311qt60503\1\python\Lib\site-packages"
    -- print("Initializing Preditor")
    -- print(getFilenamePath(getSourceFileName()))
    local preditor = python.import "preditor"
    preditor.configure "studiomax"
)

configure_preditor()
