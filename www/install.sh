#! /bin/bash

DIR=$(dirname "${VAR}")

ln -s ${DIR}/plugins/analysecharts/AnalysisCharts.py ${DIR}/plugins/AnalysisCharts.py
ln -s ${DIR}/plugins/analysecharts/www/analysischarts ${DIR}/www/analysischarts
ln -s ${DIR}/plugins/analysecharts/www/analysischarts.html ${DIR}/www/analysischarts.html

