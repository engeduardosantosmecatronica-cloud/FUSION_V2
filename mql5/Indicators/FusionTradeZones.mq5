//+------------------------------------------------------------------+
//| FusionTradeZones.mq5                                             |
//| Desenha zonas de entrada, TP, SL, suporte e resistencia do FUSION.|
//+------------------------------------------------------------------+
#property indicator_chart_window
#property indicator_plots 0
#property strict

input bool   InpAutoDetectSymbol = true;
input string InpFileName = "fusion_trade_zones.csv";
input string InpFilePrefix = "fusion_trade_zones_";
input bool   InpUseCommonFiles = true;
input bool   InpFilterChartTimeframe = true;
input int    InpPastBars = 12;
input int    InpFutureBars = 80;
input int    InpRefreshSeconds = 2;
input bool   InpShowLabels = true;
input bool   InpShowEntryArrows = true;
input bool   InpDrawBehindCandles = false;
input bool   InpShowDebugStatus = true;

string PREFIX = "FUSION_TRADE_ZONES_";

string Upper(string value)
{
   string result = value;
   StringToUpper(result);
   return result;
}

bool IsUpperLetter(ushort ch)
{
   return ch >= 'A' && ch <= 'Z';
}

string NormalizeSymbol(string symbol)
{
   string s = Upper(symbol);
   int len = StringLen(s);
   if(len >= 6)
   {
      string first6 = StringSubstr(s, 0, 6);
      bool letters = true;
      for(int i = 0; i < 6; i++)
      {
         if(!IsUpperLetter(StringGetCharacter(first6, i)))
         {
            letters = false;
            break;
         }
      }
      if(letters)
         return first6;
   }
   return s;
}

string ChartTimeframe()
{
   if(_Period == PERIOD_M5) return "M5";
   if(_Period == PERIOD_M15) return "M15";
   if(_Period == PERIOD_M30) return "M30";
   if(_Period == PERIOD_H1) return "H1";
   if(_Period == PERIOD_H4) return "H4";
   if(_Period == PERIOD_D1) return "D1";
   return "";
}

string ZoneFileName()
{
   if(!InpAutoDetectSymbol)
      return InpFileName;
   return InpFilePrefix + NormalizeSymbol(_Symbol) + ".csv";
}

color ZoneColor(string zone_type)
{
   string t = Upper(zone_type);
   if(t == "ENTRY_ZONE") return clrMediumSeaGreen;
   if(t == "TP_ZONE") return clrDodgerBlue;
   if(t == "SL_ZONE") return clrTomato;
   if(t == "SUPPORT") return clrSlateGray;
   if(t == "RESISTANCE") return clrDarkOrange;
   return clrDimGray;
}

int ZoneAlpha(string zone_type)
{
   string t = Upper(zone_type);
   if(t == "ENTRY_ZONE") return 55;
   if(t == "TP_ZONE") return 45;
   if(t == "SL_ZONE") return 50;
   return 35;
}

void ClearZones()
{
   int total = ObjectsTotal(0, 0, -1);
   for(int i = total - 1; i >= 0; i--)
   {
      string name = ObjectName(0, i, 0, -1);
      if(StringFind(name, PREFIX) == 0)
         ObjectDelete(0, name);
   }
}

void DrawStatus(string text, color clr)
{
   if(!InpShowDebugStatus)
      return;

   string obj = PREFIX + "STATUS";
   if(ObjectFind(0, obj) < 0)
      ObjectCreate(0, obj, OBJ_LABEL, 0, 0, 0);

   ObjectSetInteger(0, obj, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, obj, OBJPROP_XDISTANCE, 12);
   ObjectSetInteger(0, obj, OBJPROP_YDISTANCE, 42);
   ObjectSetInteger(0, obj, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, obj, OBJPROP_FONTSIZE, 8);
   ObjectSetInteger(0, obj, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, obj, OBJPROP_ZORDER, 100);
   ObjectSetString(0, obj, OBJPROP_FONT, "Consolas");
   ObjectSetString(0, obj, OBJPROP_TEXT, text);
}

void DrawZone(string name, string zone_type, double price1, double price2, string label, int row)
{
   int start_shift = InpPastBars < 1 ? 1 : InpPastBars;
   datetime start_time = iTime(_Symbol, _Period, start_shift);
   if(start_time <= 0)
      start_time = TimeCurrent() - PeriodSeconds(_Period) * start_shift;
   datetime end_time = TimeCurrent() + PeriodSeconds(_Period) * InpFutureBars;

   double low = MathMin(price1, price2);
   double high = MathMax(price1, price2);
   string obj = PREFIX + name;
   ObjectCreate(0, obj, OBJ_RECTANGLE, 0, start_time, high, end_time, low);
   ObjectSetInteger(0, obj, OBJPROP_COLOR, ZoneColor(zone_type));
   ObjectSetInteger(0, obj, OBJPROP_FILL, true);
   ObjectSetInteger(0, obj, OBJPROP_BACK, InpDrawBehindCandles);
   ObjectSetInteger(0, obj, OBJPROP_SELECTABLE, true);
   ObjectSetInteger(0, obj, OBJPROP_ZORDER, 5);

   if(!InpShowLabels)
      return;

   string text_obj = obj + "_LABEL";
   ObjectCreate(0, text_obj, OBJ_TEXT, 0, end_time, (low + high) / 2.0);
   ObjectSetString(0, text_obj, OBJPROP_TEXT, label);
   ObjectSetInteger(0, text_obj, OBJPROP_COLOR, ZoneColor(zone_type));
   ObjectSetInteger(0, text_obj, OBJPROP_FONTSIZE, 8);
   ObjectSetInteger(0, text_obj, OBJPROP_ANCHOR, ANCHOR_RIGHT);
   ObjectSetInteger(0, text_obj, OBJPROP_SELECTABLE, false);
}

void DrawEntryArrow(string name, double price, string signal)
{
   if(!InpShowEntryArrows)
      return;

   string s = Upper(signal);
   if(s != "BUY" && s != "SELL")
      return;

   datetime arrow_time = TimeCurrent() + PeriodSeconds(_Period) * 2;
   string obj = PREFIX + "ARROW_" + name;
   ObjectCreate(0, obj, OBJ_ARROW, 0, arrow_time, price);
   ObjectSetInteger(0, obj, OBJPROP_ARROWCODE, s == "BUY" ? 233 : 234);
   ObjectSetInteger(0, obj, OBJPROP_COLOR, s == "BUY" ? clrLimeGreen : clrTomato);
   ObjectSetInteger(0, obj, OBJPROP_WIDTH, 2);
   ObjectSetInteger(0, obj, OBJPROP_SELECTABLE, true);
   ObjectSetInteger(0, obj, OBJPROP_ZORDER, 10);
}

void RenderZones()
{
   int flags = FILE_READ | FILE_CSV | FILE_ANSI;
   if(InpUseCommonFiles)
      flags |= FILE_COMMON;

   string file_name = ZoneFileName();
   int handle = FileOpen(file_name, flags, ',');
   ClearZones();
   if(handle == INVALID_HANDLE)
   {
      DrawStatus("FUSION zones: arquivo nao encontrado - " + file_name, clrOrange);
      return;
   }

   string chart_tf = ChartTimeframe();
   bool first = true;
   int row = 0;
   int skipped_by_timeframe = 0;
   while(!FileIsEnding(handle))
   {
      string tf = FileReadString(handle);
      string zone_type = FileReadString(handle);
      string price1_raw = FileReadString(handle);
      string price2_raw = FileReadString(handle);
      string label = FileReadString(handle);
      string signal = FileReadString(handle);

      if(first)
      {
         first = false;
         if(Upper(tf) == "TIMEFRAME")
            continue;
      }

      if(tf == "" || zone_type == "")
         continue;
      if(InpFilterChartTimeframe && chart_tf != "" && Upper(tf) != chart_tf)
      {
         skipped_by_timeframe++;
         continue;
      }

      double price1 = StringToDouble(price1_raw);
      double price2 = StringToDouble(price2_raw);
      if(price1 <= 0 || price2 <= 0)
         continue;

      string full_label = StringFormat("%s %s", tf, label);
      DrawZone(IntegerToString(row), zone_type, price1, price2, full_label, row);
      if(Upper(zone_type) == "ENTRY_ZONE")
         DrawEntryArrow(IntegerToString(row), (price1 + price2) / 2.0, signal);
      row++;
   }
   FileClose(handle);

   if(row == 0)
   {
      if(InpFilterChartTimeframe && chart_tf != "" && skipped_by_timeframe > 0)
         DrawStatus("FUSION zones: sem zonas para " + NormalizeSymbol(_Symbol) + " " + chart_tf, clrOrange);
      else if(InpFilterChartTimeframe && chart_tf == "")
         DrawStatus("FUSION zones: timeframe nao suportado pelo filtro", clrOrange);
      else
         DrawStatus("FUSION zones: arquivo sem zonas validas - " + NormalizeSymbol(_Symbol), clrOrange);
   }
   else
      DrawStatus("FUSION zones: " + NormalizeSymbol(_Symbol) + " " + (chart_tf == "" ? "ALL" : chart_tf) + " | " + IntegerToString(row) + " zonas", clrSilver);
}

int OnInit()
{
   int refresh = InpRefreshSeconds < 1 ? 1 : InpRefreshSeconds;
   EventSetTimer(refresh);
   RenderZones();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   ClearZones();
}

void OnTimer()
{
   RenderZones();
   ChartRedraw(0);
}

int OnCalculate(
   const int rates_total,
   const int prev_calculated,
   const datetime &time[],
   const double &open[],
   const double &high[],
   const double &low[],
   const double &close[],
   const long &tick_volume[],
   const long &volume[],
   const int &spread[]
)
{
   return rates_total;
}
