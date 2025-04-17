macroScript PrEditor_Show
category:"PrEditor"
tooltip:"PrEditor..."
IconName:"preditor.ico"
(
    local preditor = python.import "preditor"
    preditor.launch()
)
