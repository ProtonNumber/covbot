import asyncio
import discord
import requests
import json

from babel import Locale
from babel.numbers import format_decimal
from babel.dates import format_date, format_datetime, get_timezone
from pytz import timezone, country_timezones
from os.path import isfile
from datetime import datetime
from time import time
from translate import Translator

## Add API keys in a less cursed way
ADMIN_UUID = 0 				# The discord user id of the person maintaining the bot
DISCORD_API_KEY = 0			# The API key for the bot
ADMIN_EMAIL = ""			# The admin's email, which translator uses as an API key
NEWSAPI_KEY = 0				# The API key for newsAPI

CountryData = {}
TranslateCache = {}
EmbedCache = {}
DataCache = {}
Subscriptions = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]

HelpText = ""
ListText = ""
ListContent = ""

Debug = False

def HasAdmin(User, Channel):
    if type(Channel).__name__ == "DMChannel":
        return True
    elif User.id == ADMIN_UUID:
        return True
    elif Channel.permissions_for(User).administrator:
        return True
    else:
        return False

def Format(Number, locale):
    return format_decimal(Number, format = "+#,##0.#;-#,##0.#", locale = locale)

def SaveVar(Var, File, Overwrite = True):
    if not (not Overwrite and isfile(File)):
        print("Writing " + File)
        with open(File, "w+") as File:
            json.dump(Var, File)
            File.close()
    else:
        print(File + " Exists")

def ReadVar(File):
    print(File)
    if isfile(File):
        with open(File, "r+") as File:
            JSON = json.load(File)
            File.close()
            return JSON
    else:
        return None

def CacheTranslate(lang, string, save = True):

    global TranslateCache
    
    if lang.lower() != "en":
        out = ""
        if lang not in TranslateCache:
            TranslateCache[lang] = {}          # Create a translation dictionary
        if string in TranslateCache[lang]:
            out = TranslateCache[lang][string] # If the translation is in the cache, just swap it out
        else:                                  # Otherwise, send it tp be translated
            translator = Translator(lang.replace("_", "-"),email = ADMIN_EMAIL) 
            out = translator.translate(string)
            if "MYMEMORY WARNING" not in out:  # If we've gone over our translation limit then default to english
                if save:                       # Some strings aren't worth caching. Dont cache them.
                    TranslateCache[lang][string] = out
                    SaveVar(TranslateCache, "TranslateCache.json", True)
            else:
                out = string
        return out
    else:                                      # If its already in english, then don't bother translating it.
        return string

def GetJSON(URL):
    '''Sends a GET request to URL and returns the resonse as JSON'''
    Response = requests.get(URL)
    return Response.json()

def GetCacheJSON(URL):
    global DataCache
    if URL not in DataCache:
        DataCache[URL] = GetJSON(URL)
    return DataCache[URL]

def GetCSV(URL):
    Response = requests.get(URL)
    Response = Response.text.replace("\r", "")
    RowSplit = Response.split("\n")
    CSV = []
    for i in range(len(RowSplit)):
        if RowSplit[i] != "":
            CSV.append(RowSplit[i].split(","))
    return CSV

def LoadText(File):
    File = open(File, "r+")
    Text = File.read()
    File.close()
    return Text

def LoadFiles():

    global TranslateCache
    global CountryData
    global HelpText
    global ListText
    global Subscriptions
    
    CountryData = ReadVar("CountryData.json")
    TranslateCache = ReadVar("TranslateCache.json")
    HelpText = LoadText("Help.txt")
    ListText = LoadText("List.txt")
    Subscriptions = ReadVar("Subscriptions.json")

##def CSVDataString(CSVConfig, CSVData, Key, locale):
##    Today = int(CSVConfig["Today"])
##    Yesterday = int(CSVConfig["Yesterday"])
##    try:
##        return Format(CSVData[Today][int(CSVConfig[Key])], locale) + " (" + Format(int(CSVData[Today][int(CSVConfig[Key])]) - int(CSVData[Yesterday][int(CSVConfig[Key])]), locale) + ")"
##    except:
##        return "Not Reported"

def CSVDataString(CSVConfig, CSVData, Key, locale):

    i = int(CSVConfig["Order"])
    Order = i
    Output = ""

    while abs(i) < len(CSVData):
        try:
            Output = Format(CSVData[i][int(CSVConfig[Key])], locale)[1:]
        except:
            i = i + Order
        else:
            break

    if Output == "":
        Output = "Not Reported"
    else:
        try:
            Output = Output + " (" + Format(int(CSVData[i][int(CSVConfig[Key])]) - int(CSVData[i + Order][int(CSVConfig[Key])]), locale) + ")"
        except:
            pass

    return Output
    
def GetDataCSV(Country, locale):
    CSVConfig = ReadVar(Country["CSV"])
    CSVData = GetCSV(CSVConfig["URL"])

    DataOut = {}
    DataOut["Deaths"] = CSVDataString(CSVConfig, CSVData, "Deaths", locale)
    DataOut["Confirmed"] = CSVDataString(CSVConfig, CSVData, "Confirmed", locale)
    DataOut["Recovered"] = CSVDataString(CSVConfig, CSVData, "Recovered", locale)
    DataOut["Active"] = CSVDataString(CSVConfig, CSVData, "Active", locale)
    DataOut["Vaccinated"] = CSVDataString(CSVConfig, CSVData, "Vaccinated", locale)
    DataOut["Date"] = format_date(datetime.strptime(CSVData[int(CSVConfig["Order"])][int(CSVConfig["Date"])], CSVConfig["DateForm"]), format = "short", locale=Locale.parse("und_"+Country["ISO2"]))
    DataOut["Source"] = CSVConfig["Source"]

    return DataOut

def GetData(Country, locale):
    DataOut = {}
    try:
        DataOut = GetDataCSV(Country, locale)        # The fallback method is now the primary method. Fuck you.
    except:
        try:
            RawData = GetCacheJSON("https://api.covid19api.com/summary")["Countries"]     # Get Data from COVID19API (I should really cache this)
            Data = next(item for item in RawData if item["Slug"] == Country["Slug"]) # Try to find the slug in COVID19API's Data
        except:
            DataOut["Active"] = "No Data"
            DataOut["Deaths"] = "No Data" 
            DataOut["Confirmed"] = "No Data"         # If the fallback doesn't work, just say there's no data.
            DataOut["Recovered"] = "No Data"         # This probably means there was no fallback for that country
            DataOut["Vaccinated"] = "No Data"
            DataOut["Date"] = "Unknown"
            DataOut["Source"] = "No data is available. Sorry!"
        else:
            DataOut["Active"] = Format(Data["TotalConfirmed"] - Data["TotalRecovered"] - Data["TotalDeaths"], locale) + " (" + Format(Data["NewConfirmed"] - Data["NewRecovered"] - Data["NewDeaths"], locale) + ")"
            DataOut["Confirmed"] = Format(Data["TotalConfirmed"], locale) + " (" + Format(Data["NewConfirmed"], locale) + ")"
            DataOut["Deaths"] = Format(Data["TotalDeaths"], locale) + " (" + Format(Data["NewDeaths"], locale) + ")"
            DataOut["Recovered"] = Format(Data["TotalRecovered"], locale) + " (" + Format(Data["NewRecovered"], locale) + ")"
            DataOut["Vaccinated"] = "No Data"
            DataOut["Date"] = format_datetime(datetime.strptime(Data["Date"].split(".")[0], "%Y-%m-%dT%H:%M:%S"), format = "short", locale=locale)
            DataOut["Source"] = "Data is sourced from covid19api.com."

    return DataOut

def GetGlobalData(locale):
    Data = GetCacheJSON()["Global"]      # Get Data from COVID19API (I should really cache this)
    DataOut = {}
    DataOut["Active"] = Format(Data["TotalConfirmed"] - Data["TotalRecovered"] - Data["TotalDeaths"], locale) + " (" + Format(Data["NewConfirmed"] - Data["NewRecovered"] - Data["NewDeaths"], locale) + ")"
    DataOut["Confirmed"] = Format(Data["TotalConfirmed"], locale) + " (" + Format(Data["NewConfirmed"], locale) + ")"
    DataOut["Deaths"] = Format(Data["TotalDeaths"], locale) + " (" + Format(Data["NewDeaths"], locale) + ")"
    DataOut["Recovered"] = Format(Data["TotalRecovered"], locale) + " (" + Format(Data["NewRecovered"], locale) + ")"
    DataOut["Date"] = format_date(format = "short", locale=locale)
    DataOut["Source"] = "Data is sourced from covid19api.com."
    return DataOut

def StatString(Language, Text, Data, Critical = True):
    Data = Data.replace(" (+0)", "")
    if Data != "No Data" and Data != "Not Reported" :
        return (CacheTranslate(Language, Text) + " " + Data + "\n").replace(" +", " ")
    elif not Critical:
        return ""
    else:
        return CacheTranslate(Language, Text) + " " + Data + "\n".replace(" +", " ")
    
def CreateUpdateEmbed(Country, Language = "en"):
    if Language == "" and Country["Country"] != "the World":
        locale = Locale.parse("und_"+Country["ISO2"]) # Find an appropriate Locale for a country
        Language = locale.language                    # Find the language of that country
    elif Country["Country"] != "the World":
        locale = Locale(Language)
    else:
        locale = Locale("en")

    Now = datetime.utcnow()
    
    if Country["Country"] != "the World":
        Timezone = country_timezones[Country["ISO2"]][0]
        Data = GetData(Country, locale) # Get the data strings
    else:
        Timezone = country_timezones["GB"][0]
        Data = GetGlobalData(locale)    # Get the data strings
        
    DateStr = format_date(format = "full" ,date = Now.astimezone(timezone(Timezone)), locale = locale)

    News = GetCacheJSON("http://newsapi.org/v2/top-headlines?sources=bbc-news&apiKey=" + NEWSAPI_KEY)
    
    # This entire chunck of code is just translating and packaging the strings

    Header = CacheTranslate(Language, "Covbot Update " + Country["Alias"])
    StatTitle = CacheTranslate(Language, "It is " + DateStr + ". Here are the latest coronavirus statistics for "+ Country["Country"] + ":", False)

    CaseText = StatString(Language,"Confirmed Cases:", Data["Confirmed"])
    DeathsText = StatString(Language, "Confirmed Deaths:", Data["Deaths"])
    ActiveText = StatString(Language,"Approximate Active:", Data["Active"], False)
    RecoveriesText = StatString(Language,"Confirmed Recoveries:", Data["Recovered"], False)
    VaccineText = StatString(Language,"Confirmed Vaccinations:", Data["Vaccinated"], False)
    
    DataSource = "\n" + CacheTranslate(Language, Data["Source"])
    
    StatValue = CaseText + DeathsText + VaccineText + DataSource

    NewsTitle = CacheTranslate(Language, "Here are the top news stories from BBC News:")
    
    Articles = "[" + News["articles"][0]["title"] + "](" + News["articles"][0]["url"] + ") \n[" + News["articles"][1]["title"] + "](" + News["articles"][1]["url"] + ") \n[" + News["articles"][2]["title"] + "](" + News["articles"][2]["url"] + ") \n \n"
    NewsSource = CacheTranslate(Language,"Headlines sourced using NewsAPI.").replace("NewsAPI", "[NewsAPI](https://newsapi.org)")

    NewsValue = Articles + NewsSource

    Footer = CacheTranslate(Language,"Last Update:") + " " + Data["Date"]

    # Yeet the strings into an embed
    
    embed = discord.Embed(colour=discord.Colour(int(Country["Colour"])))
    embed.set_footer(text = Footer)
    embed.set_author(name=Header, icon_url="attachment://Thumbnail.png")
    embed.add_field(name=StatTitle, value=StatValue, inline = False)
    embed.add_field(name=NewsTitle, value=NewsValue, inline = False)

    return embed

def FindCountry(ISO2, CheckAlias = False):

    global CountryData
    ISO2 = ISO2.lower()
    return next((item for item in CountryData if item["ISO2"].lower() == ISO2 or (CheckAlias and item["Alias"].lower() == ISO2)), None)

def ListGen():

    global ListContent
    global CountryData

    try:
        RawData = GetCacheJSON("https://api.covid19api.com/summary")["Countries"]
        ListFormat(RawData)
    except:
        RawData = ReadVar("summary.json")["Countries"]
        ListFormat(RawData)


def ListFormat(RawData):

    global ListContent
    global CountryData

    Countries = []
    ISO2s = []
    ListContent = []
    
    for C in RawData:
        ISO2s.append(C["CountryCode"])

    for C in CountryData:
        if C["ISO2"] in ISO2s or "CSV" in C:
            if C["ISO2"] == C["Alias"]:
                ValidCodes = C["ISO2"]
            else:
                ValidCodes = C["Alias"] + " / " + C["ISO2"]
            SpaceLength = 40-len(C["Country"]) - len(ValidCodes) - 2
            if not ("Hide" in C):
                Countries.append(C["Country"] + " " + ("." * SpaceLength) + " " + ValidCodes)

    Countries.sort()

    i = 0
    j = 0
    ListContent.append("```")

    while j < len(Countries):
        if len(ListContent[i]) < 1850:
            k = 1
            ListContent[i] = ListContent[i] + "\n" + Countries[j]
            while k < 3:
                try:
                    ListContent[i] = ListContent[i] + ", " + Countries[j + k]
                    k = k + 1
                except:
                    break
            
            j = j + 3
        else:
            i = i + 1
            ListContent.append("```")

def IsInt(Int):
    try:
        int(Int)
    except:
        return False
    else:
        return True

def IsLang(Lang):
    try:
        Locale(Lang)
    except:
        return False
    else:
        return True

async def SubValidate(Channel, Content):
    Split = Content.split()
    Out = {}
    try:
        Out["ISO2"] = Split[2]
        Out["Time"] = Split[3]
    except:
        await Channel.send(content = "We can't parse that, please try again.")
    else:
        try:
            Out["Lang"] = Split[4]
        except:
            Out["Lang"] = ""

        Out["Country"] = FindCountry(Out["ISO2"], True)

        if Out["Country"] != None:
            Out["ISO2"] = Out["Country"]["ISO2"]
            if IsInt(Out["Time"]):
                if IsLang(Out["Lang"]) or Out["Lang"] == "":
                    Out["Time"] = int(Out["Time"])
                    return Out
                else:
                    await Channel.send(content = "We don't recognise this language, please try again.")
                    return None
            else:
                await Channel.send(content = "That doesn't seem to be a valid time, please try again.")
                return None
        else:
            await Channel.send(content = "We don't seem to recognise this country code, please try again.")
            return None

async def SendEmbed(ChannelID, Content, Embed, Thumbnail):
    try:
        file = discord.File(Thumbnail, filename="Thumbnail.png")
        await client.get_channel(ChannelID).send(content = Content, embed = Embed, file = file)
    except:
        print("Channel Not Found")
        

client = discord.Client()

@client.event
async def Main():
    
    global CountryData
    global Subscriptions
    global DataCache
    global EmbedCache

    while True:
    
        LoadFiles()
        ListGen()

        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/cb help"))

        Now = datetime.now()
        Hour = Now.hour

        for h in range(Hour, 24):
            DataCache = {}
            EmbedCache = {}
            print(h)
            try:
                Subscriptions = ReadVar("Subscriptions.json")
                for Sub in Subscriptions[h]:
                    Country = FindCountry(Sub["ISO2"])
                    if Country != None:
                        if Country["ISO2"] in EmbedCache and Sub["Lang"] in EmbedCache[Country["ISO2"]]:
                            Embed = EmbedCache[Country["ISO2"]][Sub["Lang"]]
                        else:
                            Embed = CreateUpdateEmbed(Country, Sub["Lang"])
                        await SendEmbed(Sub["Channel"], "Here's today's Covbot update for " + Country["Country"] + ":", Embed, Country["Image"])
            except Exception as e:
                print(str(e))
                SaveVar(str(e), "log/" + str(time()) + ".txt")
            await asyncio.sleep(3600 - datetime.now().minute * 60) # Timings dont have to be exact, they just have to be close enough
    
@client.event
async def on_message(message):

    global Subscriptions
    global CountryData
    global HelpText
    global ListText
    global ListContent

    Author = message.author
    Channel = message.channel
    Content = message.content.lower()

    if Author.id != /*ADMIN*/:
        if Content.startswith("/cb subscribe") and HasAdmin(Author, Channel):
            SubData = await SubValidate(Channel, Content)
            if SubData != None:
                try:
                    Subscription = {"Channel" : Channel.id, "ISO2" : SubData["ISO2"], "Lang" : SubData["Lang"]}
                    if Subscription in Subscriptions[int(SubData["Time"])]:
                        await Channel.send(content = "That subscription already exists. Sorry!")
                    else:
                        Subscriptions[int(SubData["Time"])].append(Subscription)
                        SaveVar(Subscriptions, "Subscriptions.json")
                        await Channel.send(content = "This channel will now recive updates for " + SubData["Country"]["Country"] + " at " + str(SubData["Time"]) + ":00 UTC.")
                    try:
                        Country = FindCountry(SubData["ISO2"], True)
                        if Country["ISO2"] in EmbedCache and SubData["Lang"] in EmbedCache[SubData["ISO2"]]:
                            Embed = EmbedCache[SubData["ISO2"]][SubData["Lang"]]
                        else:
                            Embed = CreateUpdateEmbed(Country, SubData["Lang"])
                        await SendEmbed(Channel.id, "Here's the latest Covbot Update for " + Country["Country"] + ".", Embed, Country["Image"])
                    except:
                        await Channel.send(content = "We couldn't get the latest update for you. Sorry!")
                except:
                    await Channel.send(content = "Something went wrong, please try again.")
        elif Content.startswith("/cb unsubscribe") and HasAdmin(Author, Channel):
            SubData = await SubValidate(Channel, Content)
            if SubData != None:
                Subscription = {"Channel" : Channel.id, "ISO2" : SubData["ISO2"], "Lang" : SubData["Lang"]}
                try:
                    Subscriptions[int(SubData["Time"])].remove(Subscription)
                except:
                    await Channel.send(content = "We can't find that subscription, please try again.")
                else:
                    SaveVar(Subscriptions, "Subscriptions.json")
        elif Content.startswith("/cb update"):
            Data = Content.split()
            ISO2 = Data[2]
            Country = FindCountry(ISO2, True)
            GetData(Country, "en_uk")
            try:
                Lang = Data[3]
            except:
                Lang = ""
            if Country != None:
                try:
                    if Country["ISO2"] in EmbedCache and Lang in EmbedCache[Country["ISO2"]]:
                        Embed = EmbedCache[Country["ISO2"]][Lang]
                    else:
                        Embed = CreateUpdateEmbed(Country, Lang)
                    await SendEmbed(Channel.id, "Here's the latest Covbot Update for " + Country["Country"] + ":", Embed, Country["Image"])
                except:
                    await Channel.send(content = "We can't parse that, please try again.")
            else:
                await Channel.send(content = "We don't seem to recognise this country code, please try again.")
        elif Content == "/cb list":
            await Author.send(content = ListText)
            for I in ListContent:
                await Author.send(content = I + "```")
            await Channel.send(content = "We've sent you the list.")
        elif Content == "/cb help":
            await Author.send(content = HelpText)
            await Channel.send(content = "We've sent you the documentation.")
        elif Content == "/cb debug start" and Author.id == ADMIN_UUID:
            await Author.send("Starting!")
            await Main()
        elif Content == "/cb debug loadfiles" and Author.id == ADMIN_UUID:
            LoadFiles()
            await Author.send("Reloading!")

LoadFiles()
ListGen()

client.run(DISCORD_API_KEY)






    
