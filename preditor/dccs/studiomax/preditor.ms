
function configure_preditor = (
    local pysite = python.import "site"
    local WinEnv = dotNetClass "System.Environment"
    -- If the env var PREDITOR_SITE is set, add its packages to python
    local venv_path = WinEnv.GetEnvironmentVariable "PREDITOR_SITE"
    if venv_path != undefined do (
        print("Preditor is adding python site: " + venv_path)
        pysite.addsitedir venv_path
    )
    -- Configure preditor, adding excepthook etc.
    local preditor = python.import "preditor"
    preditor.configure "studiomax"
)

configure_preditor()
