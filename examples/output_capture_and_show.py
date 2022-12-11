import logging

import preditor

print("1. logging.root.level: {}".format(logging.root.level))
print("Printed before stream manager installed. Doesn't show up in PrEditor")
preditor.configure('PrEditor')
print("2. logging.root.level: {}".format(logging.root.level))
print("Printed after stream manager installed. Shows up in PrEditor")

preditor.launch()
print("3. logging.root.level: {}".format(logging.root.level))
