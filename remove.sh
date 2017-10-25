#! /bin/bash

# To store the path of the executing script's directory in var `__DIR__`:
DIR="$(cd "$(dirname "${0}")"; echo "$(pwd)")"

ln -s ${DIR}/plugins/analysecharts/AnalysisCharts.py ${DIR}/plugins/AnalysisCharts.py
ln -s ${DIR}/plugins/analysecharts/www/analysischarts ${DIR}/www/analysischarts
ln -s ${DIR}/plugins/analysecharts/www/analysischarts.html ${DIR}/www/analysischarts.html

