#! /bin/bash

# To store the path of the executing script's directory in var `__DIR__`:
DIR="$(cd "$(dirname "${0}")"; echo "$(pwd)")"

rm ${DIR}/plugins/AnalysisCharts.py
rm ${DIR}/www/analysischarts
rm ${DIR}/www/analysischarts.html

