# CryptoCoinLendingBotPlugins
Some Plugins for Crypto Coin Lending Bot aka Poloniex Lending Bot


## Install ##

- git submodule add -f https://github.com/MoonMaker/CryptoCoinLendingBotPlugins.git plugins/analysecharts
- git submodule foreach git pull
- chmod +x plugins/analysecharts/*.sh
- plugins/analysecharts/install.sh


## Configure ##
Add AnalysisCharts to plugins:
plugins = AccountStats,Charts,**AnalysisCharts**

Change MarketAnalysis keep_history_seconds to maximum of 1209600s:

[MarketAnalysis]
keep_history_seconds = 1209600


## Testing ##
Go to your bot webpage e.g. ```127.0.0.1:7777/analysischarts.html```


## Remove ##

- plugins/analysecharts/remove.sh
- git submodule deinit -f -- plugins/analysecharts
- git rm --cached plugins/analysecharts
- rm -R plugins/analysecharts
