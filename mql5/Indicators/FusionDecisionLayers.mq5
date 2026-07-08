//+------------------------------------------------------------------+
//| FusionDecisionLayers.mq5                                         |
//| Painel visual das camadas de decisao do FUSION.                  |
//+------------------------------------------------------------------+
#property indicator_chart_window
#property indicator_plots 0
#property strict

input bool   InpAutoDetectSymbol = true;
input string InpFileName = "fusion_decision_layers.csv";
input string InpFilePrefix = "fusion_decision_layers_";
input bool   InpUseCommonFiles = true;
input bool   InpFilterChartTimeframe = true;
input int    InpCorner = CORNER_LEFT_UPPER;
input int    InpX = 12;
input int    InpY = 36;
input int    InpLineHeight = 15;
input int    InpFontSize = 8;
input string InpFont = "Consolas";
input int    InpRefreshSeconds = 2;
input bool   InpShowReason = false;

string PREFIX = "FUSION_DECISION_LAYERS_";
int PanelX = 0;
int PanelY = 0;
int LastRows = 0;

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
   if(StringLen(s) >= 6)
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

string LayerFileName()
{
   if(!InpAutoDetectSymbol)
      return InpFileName;
   return InpFilePrefix + NormalizeSymbol(_Symbol) + ".csv";
}

color StatusColor(string status)
{
   string s = Upper(status);
   if(s == "OK")
      return clrLimeGreen;
   if(s == "WARN")
      return clrGold;
   if(s == "BLOCK")
      return clrTomato;
   return clrSilver;
}

string ShortLayerName(string layer)
{
   string l = layer;
   StringReplace(l, "market_briefing", "briefing");
   StringReplace(l, "market_regime", "regime");
   StringReplace(l, "volatility_engine", "vol");
   StringReplace(l, "session_context", "sessao");
   StringReplace(l, "portfolio_exposure", "portfolio");
   StringReplace(l, "market_structure", "estrutura");
   StringReplace(l, "feature_engineering", "features");
   StringReplace(l, "entry_timing", "timing");
   StringReplace(l, "risk_engine", "risk");
   StringReplace(l, "candle_price", "candle");
   StringReplace(l, "ema_alignment", "emas");
   StringReplace(l, "confidence_calibration", "confidence");
   StringReplace(l, "consensus_engine", "consensus");
   StringReplace(l, "opportunity_engine", "opportunity");
   StringReplace(l, "floating_loss_guard", "loss_guard");
   return l;
}

void DrawLabel(string name, string text, int row, color clr)
{
   string obj = PREFIX + name;
   if(ObjectFind(0, obj) < 0)
      ObjectCreate(0, obj, OBJ_LABEL, 0, 0, 0);

   ObjectSetInteger(0, obj, OBJPROP_CORNER, InpCorner);
   ObjectSetInteger(0, obj, OBJPROP_XDISTANCE, PanelX);
   ObjectSetInteger(0, obj, OBJPROP_YDISTANCE, PanelY + row * InpLineHeight);
   ObjectSetInteger(0, obj, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, obj, OBJPROP_FONTSIZE, InpFontSize);
   ObjectSetInteger(0, obj, OBJPROP_SELECTABLE, true);
   ObjectSetInteger(0, obj, OBJPROP_SELECTED, false);
   ObjectSetInteger(0, obj, OBJPROP_ZORDER, 110);
   ObjectSetString(0, obj, OBJPROP_FONT, InpFont);
   ObjectSetString(0, obj, OBJPROP_TEXT, text);
}

void ClearPanel()
{
   int total = ObjectsTotal(0, 0, -1);
   for(int i = total - 1; i >= 0; i--)
   {
      string name = ObjectName(0, i, 0, -1);
      if(StringFind(name, PREFIX) == 0)
         ObjectDelete(0, name);
   }
}

void RenderPanel()
{
   int flags = FILE_READ | FILE_CSV | FILE_ANSI;
   if(InpUseCommonFiles)
      flags |= FILE_COMMON;

   int handle = FileOpen(LayerFileName(), flags, ',');
   if(handle == INVALID_HANDLE)
   {
      ClearPanel();
      LastRows = 0;
      DrawLabel("TITLE", "FUSION layers " + NormalizeSymbol(_Symbol) + " | sem arquivo", 0, clrOrange);
      return;
   }

   string chart_tf = ChartTimeframe();
   int row = 0;
   bool first = true;
   DrawLabel("TITLE", NormalizeSymbol(_Symbol) + " " + chart_tf + " layers", row, clrWhite);
   row++;

   while(!FileIsEnding(handle))
   {
      string tf = FileReadString(handle);
      string layer = FileReadString(handle);
      string status = FileReadString(handle);
      string score = FileReadString(handle);
      string state = FileReadString(handle);
      string reason = FileReadString(handle);

      if(first)
      {
         first = false;
         if(Upper(tf) == "TIMEFRAME")
            continue;
      }
      if(tf == "" || layer == "")
         continue;
      if(InpFilterChartTimeframe && chart_tf != "" && Upper(tf) != chart_tf)
         continue;

      string text = StringFormat("%-13s %-5s %s", ShortLayerName(layer), Upper(status), score);
      if(InpShowReason && reason != "")
         text += " " + reason;
      DrawLabel("ROW_" + IntegerToString(row), text, row, StatusColor(status));
      row++;
   }
   FileClose(handle);

   for(int stale = row; stale < LastRows; stale++)
      ObjectDelete(0, PREFIX + "ROW_" + IntegerToString(stale));
   LastRows = row;
}

int RowFromObjectName(string obj)
{
   string row_prefix = PREFIX + "ROW_";
   if(StringFind(obj, row_prefix) != 0)
      return 0;
   return (int)StringToInteger(StringSubstr(obj, StringLen(row_prefix)));
}

int OnInit()
{
   PanelX = InpX;
   PanelY = InpY;
   int refresh = InpRefreshSeconds < 1 ? 1 : InpRefreshSeconds;
   EventSetTimer(refresh);
   RenderPanel();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   ClearPanel();
}

void OnTimer()
{
   RenderPanel();
   ChartRedraw(0);
}

void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
{
   if(id != CHARTEVENT_OBJECT_DRAG || StringFind(sparam, PREFIX) != 0)
      return;
   int row = RowFromObjectName(sparam);
   int x = (int)ObjectGetInteger(0, sparam, OBJPROP_XDISTANCE);
   int y = (int)ObjectGetInteger(0, sparam, OBJPROP_YDISTANCE);
   PanelX = x;
   PanelY = y - row * InpLineHeight;
   RenderPanel();
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
