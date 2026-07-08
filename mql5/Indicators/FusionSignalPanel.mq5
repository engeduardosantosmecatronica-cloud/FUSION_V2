//+------------------------------------------------------------------+
//| FusionSignalPanel.mq5                                            |
//| Painel simples para exibir sinais multi-timeframe do FUSION.     |
//| Le arquivo CSV em MQL5/Common/Files ou MQL5/Files.               |
//+------------------------------------------------------------------+
#property indicator_chart_window
#property indicator_plots 0
#property strict

input string InpFileName = "fusion_signal_panel.csv";
input bool   InpAutoDetectSymbol = true;
input string InpFilePrefix = "fusion_signal_panel_";
input bool   InpUseCommonFiles = true;
input int    InpCorner = CORNER_RIGHT_LOWER;
input int    InpX = 200;
input int    InpY = 60;
input int    InpLineHeight = 16;
input int    InpFontSize = 9;
input string InpFont = "Consolas";
input bool   InpShowSymbolHeader = true;
input bool   InpEnableAlerts = true;
input bool   InpAlertCurrentTimeframeOnly = false;
input bool   InpPlayAlertSound = true;
input string InpAlertSoundFile = "alert.wav";
input bool   InpSendPushNotification = false;
input bool   InpLogAlerts = true;
input string InpAlertLogFile = "fusion_signal_alert_log.csv";
input bool   InpGlobalAlertDedupe = true;
input int    InpAlertDedupeSeconds = 60;
input bool   InpShowEntryArrow = true;
input int    InpArrowOffsetPoints = 30;
input bool   InpEnableManualOrderPrompt = true;
input string InpManualRequestFile = "fusion_manual_order_request.csv";
input string InpManualResponseFile = "fusion_manual_order_response.csv";
input bool   InpShowTradeZones = true;
input string InpTradeZonesFilePrefix = "fusion_trade_zones_";
input bool   InpTradeZonesFilterChartTimeframe = true;
input bool   InpShowSupportResistanceZones = false;
input int    InpTradeZonesPastBars = 12;
input int    InpTradeZonesFutureBars = 80;
input bool   InpTradeZonesShowLabels = true;
input bool   InpTradeZonesDrawBehindCandles = false;

string PREFIX = "FUSION_SIGNAL_PANEL_";
string ZONE_PREFIX = "FUSION_SIGNAL_PANEL_ZONE_";
int PanelX = 0;
int PanelY = 0;
int LastRows = 0;
string PanelRows[];
color PanelColors[];
string LastAlertState = "";
bool AlertsPrimed = false;
string LastManualRequestId = "";

color SignalColor(string signal)
{
   string s = Upper(signal);
   if(s == "BUY")
      return clrLimeGreen;
   if(s == "SELL")
      return clrTomato;
   if(s == "WAIT" || s == "NEUTRAL" || s == "NEUTRO")
      return clrWhite;
   return clrDarkGray;
}

string SignalText(string signal)
{
   string s = Upper(signal);
   if(s == "BUY")
      return "Buy";
   if(s == "SELL")
      return "Sell";
   if(s == "WAIT" || s == "NEUTRAL" || s == "NEUTRO")
      return "Wait";
   return signal;
}

uint TextHash(string value)
{
   uint hash = 2166136261;
   int len = StringLen(value);
   for(int i = 0; i < len; i++)
   {
      hash ^= (uint)StringGetCharacter(value, i);
      hash *= 16777619;
   }
   return hash;
}

bool ShouldEmitGlobalAlert(string active_signals)
{
   if(!InpGlobalAlertDedupe)
      return true;

   int window = InpAlertDedupeSeconds < 1 ? 1 : InpAlertDedupeSeconds;
   string key = PREFIX + "ALERT_" + NormalizeSymbol(_Symbol) + "_" + IntegerToString((int)TextHash(active_signals));
   double last = 0.0;
   if(GlobalVariableCheck(key))
      last = GlobalVariableGet(key);

   double now = (double)TimeCurrent();
   if(last > 0.0 && now - last < window)
      return false;

   GlobalVariableSet(key, now);
   return true;
}

bool IsKnownTimeframe(string value)
{
   string tf = Upper(value);
   return tf == "M5" || tf == "M15" || tf == "M30" || tf == "H1" || tf == "H4" || tf == "D1" || tf == "FINAL";
}

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
      bool first6_letters = true;
      for(int i = 0; i < 6; i++)
      {
         if(!IsUpperLetter(StringGetCharacter(first6, i)))
         {
            first6_letters = false;
            break;
         }
      }

      if(first6_letters)
         return first6;
   }

   return s;
}

string SymbolFileName()
{
   if(!InpAutoDetectSymbol)
      return InpFileName;

   return InpFilePrefix + NormalizeSymbol(_Symbol) + ".csv";
}

string TradeZonesFileName()
{
   return InpTradeZonesFilePrefix + NormalizeSymbol(_Symbol) + ".csv";
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

int OpenPanelFile(string &opened_file)
{
   int flags = FILE_READ | FILE_CSV | FILE_ANSI;
   if(InpUseCommonFiles)
      flags |= FILE_COMMON;

   opened_file = SymbolFileName();
   int handle = FileOpen(opened_file, flags, ',');
   if(handle != INVALID_HANDLE || !InpAutoDetectSymbol)
      return handle;

   return INVALID_HANDLE;
}

bool PanelFileHasAlertColumns()
{
   int flags = FILE_READ | FILE_TXT | FILE_ANSI;
   if(InpUseCommonFiles)
      flags |= FILE_COMMON;

   int handle = FileOpen(SymbolFileName(), flags);
   if(handle == INVALID_HANDLE)
      return false;

   string header = FileReadString(handle, 2048);
   FileClose(handle);
   return StringFind(Upper(header), "ALERT_SIGNAL") >= 0;
}

void ConsumeLineRest(int handle)
{
   while(!FileIsEnding(handle) && !FileIsLineEnding(handle))
      FileReadString(handle);
}

color TradeZoneColor(string zone_type)
{
   string t = Upper(zone_type);
   if(t == "ENTRY_ZONE") return clrMediumSeaGreen;
   if(t == "TP_ZONE") return clrDodgerBlue;
   if(t == "SL_ZONE") return clrTomato;
   if(t == "SUPPORT") return clrSlateGray;
   if(t == "RESISTANCE") return clrDarkOrange;
   return clrDimGray;
}

bool ShouldDrawTradeZoneType(string zone_type)
{
   string t = Upper(zone_type);
   if(t == "ENTRY_ZONE" || t == "TP_ZONE" || t == "SL_ZONE")
      return true;
   if(InpShowSupportResistanceZones && (t == "SUPPORT" || t == "RESISTANCE"))
      return true;
   return false;
}

string ProbabilityText(string pbuy, string psell, string reason)
{
   if(pbuy == "" || psell == "")
   {
      if(StringFind(Upper(reason), "ERRO_DADOS") >= 0)
         return "sem dados";
      return "--/--";
   }

   return pbuy + "/" + psell;
}

void DrawLabel(string name, string text, int row, color clr)
{
   string obj = PREFIX + name;
   if(ObjectFind(0, obj) < 0)
      ObjectCreate(0, obj, OBJ_LABEL, 0, 0, 0);

   ObjectSetInteger(0, obj, OBJPROP_CORNER, InpCorner);
   ObjectSetInteger(0, obj, OBJPROP_XDISTANCE, PanelX);
   if(InpCorner == CORNER_LEFT_LOWER || InpCorner == CORNER_RIGHT_LOWER)
      ObjectSetInteger(0, obj, OBJPROP_YDISTANCE, PanelY + (LastRows - row - 1) * InpLineHeight);
   else
      ObjectSetInteger(0, obj, OBJPROP_YDISTANCE, PanelY + row * InpLineHeight);
   ObjectSetInteger(0, obj, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, obj, OBJPROP_FONTSIZE, InpFontSize);
   ObjectSetInteger(0, obj, OBJPROP_SELECTABLE, true);
   ObjectSetInteger(0, obj, OBJPROP_SELECTED, false);
   ObjectSetInteger(0, obj, OBJPROP_ZORDER, 100);
   ObjectSetString(0, obj, OBJPROP_FONT, InpFont);
   ObjectSetString(0, obj, OBJPROP_TEXT, text);
}

void DrawEntryArrow(string signal)
{
   string obj = PREFIX + "ENTRY_ARROW";
   string s = Upper(signal);

   if(!InpShowEntryArrow || (s != "BUY" && s != "SELL"))
   {
      ObjectDelete(0, obj);
      return;
   }

   datetime arrow_time = TimeCurrent();
   double offset = InpArrowOffsetPoints * _Point;
   double price = 0.0;
   int arrow_code = 0;
   color arrow_color = clrLimeGreen;

   if(s == "BUY")
   {
      double low = iLow(_Symbol, _Period, 0);
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      price = (low > 0.0 ? low : bid) - offset;
      arrow_code = 233;
      arrow_color = clrLimeGreen;
   }
   else
   {
      double high = iHigh(_Symbol, _Period, 0);
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      price = (high > 0.0 ? high : ask) + offset;
      arrow_code = 234;
      arrow_color = clrTomato;
   }

   if(ObjectFind(0, obj) < 0)
      ObjectCreate(0, obj, OBJ_ARROW, 0, arrow_time, price);
   else
      ObjectMove(0, obj, 0, arrow_time, price);

   ObjectSetInteger(0, obj, OBJPROP_ARROWCODE, arrow_code);
   ObjectSetInteger(0, obj, OBJPROP_COLOR, arrow_color);
   ObjectSetInteger(0, obj, OBJPROP_WIDTH, 2);
   ObjectSetInteger(0, obj, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, obj, OBJPROP_SELECTED, false);
   ObjectSetInteger(0, obj, OBJPROP_ZORDER, 120);
}

int RowFromObjectName(string obj)
{
   string row_prefix = PREFIX + "ROW_";
   if(StringFind(obj, row_prefix) != 0)
      return 0;

   string raw = StringSubstr(obj, StringLen(row_prefix));
   return (int)StringToInteger(raw);
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

void ClearTradeZones()
{
   int total = ObjectsTotal(0, 0, -1);
   for(int i = total - 1; i >= 0; i--)
   {
      string name = ObjectName(0, i, 0, -1);
      if(StringFind(name, ZONE_PREFIX) == 0)
         ObjectDelete(0, name);
   }
}

void DrawTradeZone(string name, string zone_type, double price1, double price2, string label)
{
   int start_shift = InpTradeZonesPastBars < 1 ? 1 : InpTradeZonesPastBars;
   datetime start_time = iTime(_Symbol, _Period, start_shift);
   if(start_time <= 0)
      start_time = TimeCurrent() - PeriodSeconds(_Period) * start_shift;
   datetime end_time = TimeCurrent() + PeriodSeconds(_Period) * InpTradeZonesFutureBars;

   double low = MathMin(price1, price2);
   double high = MathMax(price1, price2);
   string obj = ZONE_PREFIX + name;
   if(ObjectFind(0, obj) < 0)
      ObjectCreate(0, obj, OBJ_RECTANGLE, 0, start_time, high, end_time, low);
   else
   {
      ObjectMove(0, obj, 0, start_time, high);
      ObjectMove(0, obj, 1, end_time, low);
   }

   ObjectSetInteger(0, obj, OBJPROP_COLOR, TradeZoneColor(zone_type));
   ObjectSetInteger(0, obj, OBJPROP_FILL, true);
   ObjectSetInteger(0, obj, OBJPROP_BACK, InpTradeZonesDrawBehindCandles);
   ObjectSetInteger(0, obj, OBJPROP_SELECTABLE, true);
   ObjectSetInteger(0, obj, OBJPROP_ZORDER, 4);

   string text_obj = obj + "_LABEL";
   if(!InpTradeZonesShowLabels)
   {
      ObjectDelete(0, text_obj);
      return;
   }

   if(ObjectFind(0, text_obj) < 0)
      ObjectCreate(0, text_obj, OBJ_TEXT, 0, end_time, (low + high) / 2.0);
   else
      ObjectMove(0, text_obj, 0, end_time, (low + high) / 2.0);

   ObjectSetString(0, text_obj, OBJPROP_TEXT, label);
   ObjectSetInteger(0, text_obj, OBJPROP_COLOR, TradeZoneColor(zone_type));
   ObjectSetInteger(0, text_obj, OBJPROP_FONTSIZE, 8);
   ObjectSetInteger(0, text_obj, OBJPROP_ANCHOR, ANCHOR_RIGHT);
   ObjectSetInteger(0, text_obj, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, text_obj, OBJPROP_ZORDER, 5);
}

void RenderTradeZones()
{
   ClearTradeZones();
   if(!InpShowTradeZones)
      return;

   int flags = FILE_READ | FILE_CSV | FILE_ANSI;
   if(InpUseCommonFiles)
      flags |= FILE_COMMON;

   int handle = FileOpen(TradeZonesFileName(), flags, ',');
   if(handle == INVALID_HANDLE)
      return;

   bool first = true;
   int row = 0;
   string chart_tf = ChartTimeframe();
   while(!FileIsEnding(handle))
   {
      string tf = FileReadString(handle);
      string zone_type = FileReadString(handle);
      string price1_raw = FileReadString(handle);
      string price2_raw = FileReadString(handle);
      string label = FileReadString(handle);
      string signal = FileReadString(handle);
      ConsumeLineRest(handle);

      if(first)
      {
         first = false;
         if(Upper(tf) == "TIMEFRAME")
            continue;
      }

      if(tf == "" || zone_type == "")
         continue;
      if(!ShouldDrawTradeZoneType(zone_type))
         continue;
      if(InpTradeZonesFilterChartTimeframe && chart_tf != "" && Upper(tf) != chart_tf)
         continue;

      double price1 = StringToDouble(price1_raw);
      double price2 = StringToDouble(price2_raw);
      if(price1 <= 0.0 || price2 <= 0.0)
         continue;

      string full_label = StringFormat("%s %s", tf, label);
      DrawTradeZone(IntegerToString(row), zone_type, price1, price2, full_label);
      row++;
   }
   FileClose(handle);
}

void MaybeAlertSignal(string active_signals)
{
   if(!InpEnableAlerts)
      return;

   if(!AlertsPrimed)
   {
      LastAlertState = active_signals;
      AlertsPrimed = true;
      return;
   }

   if(active_signals == LastAlertState)
      return;

   LastAlertState = active_signals;
   if(active_signals == "")
      return;
   if(!ShouldEmitGlobalAlert(active_signals))
      return;

   string message = "FUSION ordem validada " + NormalizeSymbol(_Symbol) + ": " + active_signals;
   LogAlertSignal(active_signals, message);
   Alert(message);
   if(InpPlayAlertSound)
      PlaySound(InpAlertSoundFile);
   if(InpSendPushNotification)
      SendNotification(message);
}

void LogAlertSignal(string active_signals, string message)
{
   if(!InpLogAlerts)
      return;

   int flags = FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI;
   if(InpUseCommonFiles)
      flags |= FILE_COMMON;

   int handle = FileOpen(InpAlertLogFile, flags, ',');
   if(handle == INVALID_HANDLE)
   {
      Print("FUSION alert log: falha ao abrir ", InpAlertLogFile, " err=", GetLastError());
      return;
   }

   bool write_header = FileSize(handle) == 0;
   FileSeek(handle, 0, SEEK_END);

   if(write_header)
   {
      FileWrite(
         handle,
         "server_time",
         "local_time",
         "normalized_symbol",
         "chart_symbol",
         "chart_timeframe",
         "active_signals",
         "bid",
         "ask",
         "message"
      );
   }

   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   FileWrite(
      handle,
      TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS),
      TimeToString(TimeLocal(), TIME_DATE | TIME_SECONDS),
      NormalizeSymbol(_Symbol),
      _Symbol,
      ChartTimeframe(),
      active_signals,
      DoubleToString(bid, _Digits),
      DoubleToString(ask, _Digits),
      message
   );

   FileClose(handle);
}

void WriteManualOrderResponse(
   string request_id,
   string symbol,
   string broker_symbol,
   string timeframe,
   string side,
   string response
)
{
   int flags = FILE_WRITE | FILE_CSV | FILE_ANSI;
   if(InpUseCommonFiles)
      flags |= FILE_COMMON;

   int handle = FileOpen(InpManualResponseFile, flags, ',');
   if(handle == INVALID_HANDLE)
   {
      Print("FUSION manual approval: falha ao abrir resposta ", InpManualResponseFile, " err=", GetLastError());
      return;
   }

   FileWrite(handle, "request_id", "response", "time", "symbol", "broker_symbol", "timeframe", "side");
   FileWrite(
      handle,
      request_id,
      response,
      TimeToString(TimeLocal(), TIME_DATE | TIME_SECONDS),
      symbol,
      broker_symbol,
      timeframe,
      side
   );
   FileClose(handle);
}

void CheckManualOrderPrompt()
{
   if(!InpEnableManualOrderPrompt)
      return;

   int flags = FILE_READ | FILE_CSV | FILE_ANSI;
   if(InpUseCommonFiles)
      flags |= FILE_COMMON;

   int handle = FileOpen(InpManualRequestFile, flags, ',');
   if(handle == INVALID_HANDLE)
      return;

   bool first = true;
   while(!FileIsEnding(handle))
   {
      string request_id = FileReadString(handle);
      string created_at = FileReadString(handle);
      string symbol = FileReadString(handle);
      string broker_symbol = FileReadString(handle);
      string timeframe = FileReadString(handle);
      string side = FileReadString(handle);
      string pbuy = FileReadString(handle);
      string psell = FileReadString(handle);
      string tp_points = FileReadString(handle);
      string sl_points = FileReadString(handle);
      string magic = FileReadString(handle);
      string strategy = FileReadString(handle);
      string status = FileReadString(handle);
      ConsumeLineRest(handle);

      if(first)
      {
         first = false;
         if(StringFind(Upper(request_id), "REQUEST_ID") >= 0)
            continue;
      }

      if(request_id == "" || request_id == LastManualRequestId)
         continue;
      if(Upper(status) != "PENDING")
         continue;
      if(Upper(symbol) != NormalizeSymbol(_Symbol) && Upper(broker_symbol) != Upper(_Symbol))
         continue;

      LastManualRequestId = request_id;
      string message = StringFormat(
         "Fusion quer abrir ordem %s em %s\nTimeframe: %s\nP(Buy/Sell): %s/%s\nTP/SL pontos: %s/%s\nEstrategia: %s\n\nAutorizar abertura da ordem?",
         Upper(side),
         symbol,
         timeframe,
         pbuy,
         psell,
         tp_points,
         sl_points,
         strategy
      );
      int answer = MessageBox(message, "Fusion - Confirmar ordem", MB_YESNO | MB_ICONQUESTION);
      if(answer == IDYES)
         WriteManualOrderResponse(request_id, symbol, broker_symbol, timeframe, side, "APPROVED");
      else
         WriteManualOrderResponse(request_id, symbol, broker_symbol, timeframe, side, "REJECTED");
   }

   FileClose(handle);
}

void RenderPanel()
{
   string opened_file = "";
   int handle = OpenPanelFile(opened_file);
   if(handle == INVALID_HANDLE)
   {
      ClearPanel();
      LastRows = 0;
      DrawLabel("TITLE", "FUSION " + _Symbol + " | arquivo nao encontrado", 0, clrOrange);
      DrawLabel("PATH", SymbolFileName(), 1, clrSilver);
      return;
   }

   ArrayResize(PanelRows, 0);
   ArrayResize(PanelColors, 0);

   if(InpShowSymbolHeader)
   {
      ArrayResize(PanelRows, 1);
      ArrayResize(PanelColors, 1);
      PanelRows[0] = NormalizeSymbol(_Symbol);
      PanelColors[0] = clrSilver;
   }

   bool first = true;
   string chart_tf = ChartTimeframe();
   string timeframe_active_signals = "";
   string final_active_signal = "";
   string final_signal = "";
   string entry_arrow_signal = "";
   bool has_final_row = false;
   while(!FileIsEnding(handle))
   {
      string tf = FileReadString(handle);
      string signal = FileReadString(handle);
      string pbuy = FileReadString(handle);
      string psell = FileReadString(handle);
      string reason = FileReadString(handle);
      string alert_signal = FileReadString(handle);
      string alert_reason = FileReadString(handle);
      ConsumeLineRest(handle);

      if(first)
      {
         first = false;
         if(StringFind(Upper(tf), "TIMEFRAME") >= 0)
            continue;
      }

      if(tf == "")
         continue;

      if(!IsKnownTimeframe(tf))
         continue;

      string s = Upper(signal);
      string text = StringFormat("%-4s %-4s %s", tf, SignalText(s), ProbabilityText(pbuy, psell, reason));
      if(s == "BUY" || s == "SELL")
      {
         if(Upper(tf) == "FINAL")
         {
            has_final_row = true;
            final_signal = s;
            string final_alert_signal = Upper(alert_signal);
            if(final_alert_signal == "BUY" || final_alert_signal == "SELL")
            {
               final_active_signal = "FINAL " + final_alert_signal;
               entry_arrow_signal = final_alert_signal;
            }
         }
         else if(!InpAlertCurrentTimeframeOnly || chart_tf == "" || Upper(tf) == chart_tf)
         {
            string tf_alert_signal = Upper(alert_signal);
            if(tf_alert_signal == "BUY" || tf_alert_signal == "SELL")
            {
               if(timeframe_active_signals != "")
                  timeframe_active_signals += " | ";
               timeframe_active_signals += Upper(tf) + " " + tf_alert_signal;
               if(entry_arrow_signal == "")
                  entry_arrow_signal = tf_alert_signal;
            }
         }
      }
      else if(Upper(tf) == "FINAL")
      {
         has_final_row = true;
         final_signal = s;
      }
      int next = ArraySize(PanelRows);
      ArrayResize(PanelRows, next + 1);
      ArrayResize(PanelColors, next + 1);
      PanelRows[next] = text;
      PanelColors[next] = SignalColor(s);
   }

   int old_rows = LastRows;
   int row = ArraySize(PanelRows);
   LastRows = row;
   for(int i = 0; i < row; i++)
      DrawLabel("ROW_" + IntegerToString(i), PanelRows[i], i, PanelColors[i]);

   for(int stale = row; stale < old_rows; stale++)
      ObjectDelete(0, PREFIX + "ROW_" + IntegerToString(stale));

   FileClose(handle);
   string active_signals = has_final_row ? final_active_signal : timeframe_active_signals;
   DrawEntryArrow(entry_arrow_signal);
   MaybeAlertSignal(active_signals);
}

int OnInit()
{
   PanelX = InpX;
   PanelY = InpY;
   EventSetTimer(2);
   RenderTradeZones();
   RenderPanel();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   ClearTradeZones();
   ClearPanel();
}

void OnTimer()
{
   RenderTradeZones();
   RenderPanel();
   CheckManualOrderPrompt();
   ChartRedraw(0);
}

void OnChartEvent(
   const int id,
   const long &lparam,
   const double &dparam,
   const string &sparam
)
{
   if(id != CHARTEVENT_OBJECT_DRAG)
      return;

   if(StringFind(sparam, PREFIX) != 0)
      return;

   int row = RowFromObjectName(sparam);
   int x = (int)ObjectGetInteger(0, sparam, OBJPROP_XDISTANCE);
   int y = (int)ObjectGetInteger(0, sparam, OBJPROP_YDISTANCE);

   PanelX = x;
   if(InpCorner == CORNER_LEFT_LOWER || InpCorner == CORNER_RIGHT_LOWER)
      PanelY = y - (LastRows - row - 1) * InpLineHeight;
   else
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
