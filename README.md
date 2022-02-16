# Covbot
A simple discord bot that provides daily updates on covid statistics and the news. Neatly formats this info into embeds and even provides machine translations:

![image](https://user-images.githubusercontent.com/77733928/154263523-a8f72158-ccc6-4b48-b92e-6360eb11aa91.png)

Primarily uses covid19api.com for it's covid data, however if more accurate or comprehensive data is desired then it can use other APIs that output to CSV  by adding to CountryData.json and making an entry in data. Currently configured to take data from Public Health England and data.gov.hk.

You'll need to generate API keys for [NewsAPI](https://newsapi.org/), Discord, and provide an email for [MyMemory](https://mymemory.translated.net/). You can add these in at the top of CovbotV2.py.

Uses [Freepic - Flaticon's country flags pack](https://www.flaticon.com/packs/countrys-flags), which are not included under the GPL3 license. 
