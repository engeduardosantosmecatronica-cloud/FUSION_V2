//+------------------------------------------------------------------+
//| FusionMt5Bridge.mq5                                              |
//| Envia ticks reais do grafico MT5 para o Fusion Pro via TCP local. |
//+------------------------------------------------------------------+
#property strict

#define FUSION_BRIDGE_VERSION "MT5-FUSION-BRIDGE-MULTI-v7"

input string InpHost = "127.0.0.1";
input int    InpPort = 45678;
input int    InpReconnectSeconds = 2;
input bool   InpSendRecentCandles = false;
input bool   InpAllowLegacyBulkHistory = false;
input int    InpHistoryBars = 180;
input int    InpHistoryDays = 30;
input int    InpMinHistoryBars = 300;
input int    InpHistoryBatchSize = 250;
input bool   InpSyncCurrentCandle = true;
input bool   InpUseFusionSignalAssets = true;
input string InpSymbols = "";
input bool   InpSendAllMonitoredTicks = false;
input bool   InpOnlySendRequestedAsset = true;
input bool   InpSendHeartbeat = true;
input bool   InpDebugLog = true;
input bool   InpEnableSocketBridge = true;
input bool   InpAllowFusionOrders = false;
input string InpFusionExecutionMode = "MANUAL"; // MANUAL ou AUTOMATIC
input string InpExecutionControlFile = "fusion_execution_control.csv";
input bool   InpExportSnapshotFiles = true;
input string InpSnapshotTimeframes = "M5,M15,M30,H1,H4,D1";
input int    InpSnapshotBars = 200;
input int    InpSnapshotExportIntervalSeconds = 1;

int Socket = INVALID_HANDLE;
datetime LastConnectAttempt = 0;
datetime LastHeartbeat = 0;
int HeartbeatFailCount = 0;
datetime LastCurrentCandleSync = 0;
datetime LastTickLog = 0;
datetime LastSnapshotExport = 0;
ulong SentTicks = 0;
ulong SentCandles = 0;
bool HelloSent = false;
bool HistorySyncActive = false;
bool HistorySyncDone = false;
int HistoryNextShift = 0;
int HistorySentInSession = 0;
int HistorySymbolIndex = 0;
bool DemandHistoryActive = false;
string DemandHistorySymbol = "";
ENUM_TIMEFRAMES DemandHistoryPeriod = PERIOD_CURRENT;
long DemandHistoryFrom = 0;
uint DemandHistoryLimit = 0;
uint DemandHistorySent = 0;
int DemandHistoryNextShift = 0;
string ActiveStreamSymbol = "";
ENUM_TIMEFRAMES ActiveStreamPeriod = PERIOD_CURRENT;
string MonitoredSymbols[];
datetime LastTickSentTimes[];
uchar InboundBuffer[];

void Log(string message)
{
   if(InpDebugLog)
      Print("FusionMt5Bridge | ", message);
}

string Upper(string value)
{
   string result = value;
   StringToUpper(result);
   return result;
}

string TrimString(string value)
{
   string result = value;
   StringTrimLeft(result);
   StringTrimRight(result);
   return result;
}

ENUM_TIMEFRAMES TimeframeFromText(string value)
{
   string tf = Upper(TrimString(value));
   if(tf == "M1" || tf == "1M") return PERIOD_M1;
   if(tf == "M5" || tf == "5M") return PERIOD_M5;
   if(tf == "M15" || tf == "15M") return PERIOD_M15;
   if(tf == "M30" || tf == "30M") return PERIOD_M30;
   if(tf == "H1" || tf == "1H") return PERIOD_H1;
   if(tf == "H4" || tf == "4H") return PERIOD_H4;
   if(tf == "D1" || tf == "1D") return PERIOD_D1;
   return PERIOD_CURRENT;
}

string TimeframeLabel(ENUM_TIMEFRAMES period)
{
   if(period == PERIOD_M1) return "M1";
   if(period == PERIOD_M5) return "M5";
   if(period == PERIOD_M15) return "M15";
   if(period == PERIOD_M30) return "M30";
   if(period == PERIOD_H1) return "H1";
   if(period == PERIOD_H4) return "H4";
   if(period == PERIOD_D1) return "D1";
   return IntegerToString((int)period);
}

bool WriteSnapshotCsv(string symbol, ENUM_TIMEFRAMES period, string timeframe_label)
{
   int total = Bars(symbol, period);
   if(total <= 1)
      return false;

   int bars_to_export = MathMin(MathMax(InpSnapshotBars, 1), total);
   string file_name = StringFormat("fusion_mt5_snapshot_%s_%s.csv", NormalizeSymbol(symbol), timeframe_label);
   int handle = FileOpen(file_name, FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_COMMON, ',');
   if(handle == INVALID_HANDLE)
   {
      Log(StringFormat("falha ao gravar snapshot %s err=%d", file_name, GetLastError()));
      return false;
   }

   FileWrite(handle, "time", "open", "high", "low", "close", "volume");
   for(int shift = bars_to_export - 1; shift >= 0; shift--)
   {
      datetime open_time = iTime(symbol, period, shift);
      if(open_time <= 0)
         continue;

      double open = iOpen(symbol, period, shift);
      double high = iHigh(symbol, period, shift);
      double low = iLow(symbol, period, shift);
      double close = iClose(symbol, period, shift);
      long tick_volume = iVolume(symbol, period, shift);
      if(open <= 0.0 || high <= 0.0 || low <= 0.0 || close <= 0.0)
         continue;

      FileWrite(
         handle,
         (long)open_time,
         open,
         high,
         low,
         close,
         (double)MathMax(tick_volume, 0)
      );
   }

   FileClose(handle);
   return true;
}

void ExportSnapshotFiles()
{
   if(!InpExportSnapshotFiles)
      return;

   if(InpSnapshotExportIntervalSeconds > 0 && LastSnapshotExport != 0)
   {
      if((TimeCurrent() - LastSnapshotExport) < InpSnapshotExportIntervalSeconds)
         return;
   }
   LastSnapshotExport = TimeCurrent();

   string tf_parts[];
   int tf_count = StringSplit(InpSnapshotTimeframes, ',', tf_parts);
   if(tf_count <= 0)
      return;

   int total_symbols = ArraySize(MonitoredSymbols);
   for(int i = 0; i < total_symbols; i++)
   {
      string symbol = MonitoredSymbols[i];
      for(int j = 0; j < tf_count; j++)
      {
         string tf_label = TimeframeLabel(TimeframeFromText(tf_parts[j]));
         ENUM_TIMEFRAMES period = TimeframeFromText(tf_parts[j]);
         if(period == PERIOD_CURRENT)
            continue;
         WriteSnapshotCsv(symbol, period, tf_label);
      }
   }
}

void WriteExecutionControl()
{
   int handle = FileOpen(InpExecutionControlFile, FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_COMMON, ',');
   if(handle == INVALID_HANDLE)
   {
      Log(StringFormat("falha ao gravar controle de execucao %s err=%d", InpExecutionControlFile, GetLastError()));
      return;
   }

   string mode = Upper(InpFusionExecutionMode);
   if(mode != "MANUAL" && mode != "AUTOMATIC")
      mode = "MANUAL";

   FileWrite(handle, "updated_at", "allow_orders", "execution_mode", "source", "chart_symbol");
   FileWrite(
      handle,
      TimeToString(TimeLocal(), TIME_DATE | TIME_SECONDS),
      InpAllowFusionOrders ? "true" : "false",
      mode,
      "FusionMt5Bridge",
      _Symbol
   );
   FileClose(handle);
}

void PushU8(uchar &buffer[], uchar value)
{
   int size = ArraySize(buffer);
   ArrayResize(buffer, size + 1);
   buffer[size] = value;
}

void PushU16(uchar &buffer[], ushort value)
{
   int size = ArraySize(buffer);
   ArrayResize(buffer, size + 2);
   buffer[size] = (uchar)(value & 0xFF);
   buffer[size + 1] = (uchar)((value >> 8) & 0xFF);
}

void PushU32(uchar &buffer[], uint value)
{
   int size = ArraySize(buffer);
   ArrayResize(buffer, size + 4);
   for(int i = 0; i < 4; i++)
      buffer[size + i] = (uchar)((value >> (8 * i)) & 0xFF);
}

void PushU64(uchar &buffer[], ulong value)
{
   int size = ArraySize(buffer);
   ArrayResize(buffer, size + 8);
   for(int i = 0; i < 8; i++)
      buffer[size + i] = (uchar)((value >> (8 * i)) & 0xFF);
}

void PushI64(uchar &buffer[], long value)
{
   PushU64(buffer, (ulong)value);
}

void PushDouble(uchar &buffer[], double value)
{
   uchar raw[];
   ArrayResize(raw, 8);
   union DoubleBytes
   {
      double d;
      uchar b[8];
   } data;
   data.d = value;
   int size = ArraySize(buffer);
   ArrayResize(buffer, size + 8);
   for(int i = 0; i < 8; i++)
      buffer[size + i] = data.b[i];
}

void PushString(uchar &buffer[], string value)
{
   uchar raw[];
   int len = StringToCharArray(value, raw, 0, WHOLE_ARRAY, CP_UTF8);
   if(len > 0 && raw[len - 1] == 0)
      len--;
   PushU16(buffer, (ushort)len);
   int size = ArraySize(buffer);
   ArrayResize(buffer, size + len);
   for(int i = 0; i < len; i++)
      buffer[size + i] = raw[i];
}

uint Crc32(const uchar &bytes[])
{
   uint crc = 0xFFFFFFFF;
   int len = ArraySize(bytes);
   for(int i = 0; i < len; i++)
   {
      crc ^= bytes[i];
      for(int bit = 0; bit < 8; bit++)
      {
         uint mask = (uint)(-(int)(crc & 1));
         crc = (crc >> 1) ^ (0xEDB88320 & mask);
      }
   }
   return ~crc;
}

ushort ReadU16At(const uchar &buffer[], int offset)
{
   return (ushort)((ushort)buffer[offset] | ((ushort)buffer[offset + 1] << 8));
}

uint ReadU32At(const uchar &buffer[], int offset)
{
   return (uint)buffer[offset]
      | ((uint)buffer[offset + 1] << 8)
      | ((uint)buffer[offset + 2] << 16)
      | ((uint)buffer[offset + 3] << 24);
}

ulong ReadU64At(const uchar &buffer[], int offset)
{
   ulong value = 0;
   for(int i = 0; i < 8; i++)
      value |= ((ulong)buffer[offset + i] << (8 * i));
   return value;
}

long ReadI64At(const uchar &buffer[], int offset)
{
   return (long)ReadU64At(buffer, offset);
}

string ReadStringAt(const uchar &buffer[], int &offset)
{
   ushort len = ReadU16At(buffer, offset);
   offset += 2;
   if(len == 0)
      return "";

   uchar raw[];
   ArrayResize(raw, len + 1);
   for(int i = 0; i < len; i++)
      raw[i] = buffer[offset + i];
   raw[len] = 0;
   offset += len;
   return CharArrayToString(raw, 0, len, CP_UTF8);
}

void RemoveInboundPrefix(int count)
{
   int total = ArraySize(InboundBuffer);
   if(count >= total)
   {
      ArrayResize(InboundBuffer, 0);
      return;
   }

   for(int i = count; i < total; i++)
      InboundBuffer[i - count] = InboundBuffer[i];
   ArrayResize(InboundBuffer, total - count);
}

bool SendPayload(const uchar &payload[])
{
   if(Socket == INVALID_HANDLE)
      return false;

   uchar frame[];
   PushU8(frame, 'F');
   PushU8(frame, 'U');
   PushU8(frame, 'S');
   PushU8(frame, 'M');
   PushU8(frame, 'T');
   PushU8(frame, '5');
   PushU16(frame, 1);
   PushU32(frame, (uint)ArraySize(payload));
   PushU32(frame, Crc32(payload));

   int header_size = ArraySize(frame);
   int payload_size = ArraySize(payload);
   ArrayResize(frame, header_size + payload_size);
   for(int i = 0; i < payload_size; i++)
      frame[header_size + i] = payload[i];

   int sent = SocketSend(Socket, frame, ArraySize(frame));
   if(sent != ArraySize(frame))
   {
      Log(StringFormat("SocketSend falhou/parcial sent=%d expected=%d err=%d", sent, ArraySize(frame), GetLastError()));
      return false;
   }
   return true;
}

bool SendHello()
{
   uchar payload[];
   PushU8(payload, 1);
   PushString(payload, FUSION_BRIDGE_VERSION);
   PushU64(payload, (ulong)AccountInfoInteger(ACCOUNT_LOGIN));
   PushString(payload, AccountInfoString(ACCOUNT_SERVER));
   return SendPayload(payload);
}

bool SendHeartbeat()
{
   uchar payload[];
   PushU8(payload, 2);
   PushI64(payload, (long)TimeCurrent());
   return SendPayload(payload);
}

bool SendTick(string symbol)
{
   return SendTickForPeriod(symbol, _Period);
}

bool SendTickForPeriod(string symbol, ENUM_TIMEFRAMES period)
{
   MqlTick tick;
   if(!SymbolInfoTick(symbol, tick))
   {
      Log(StringFormat("SymbolInfoTick falhou symbol=%s err=%d", symbol, GetLastError()));
      return false;
   }

   double last = tick.last;
   if(last <= 0.0)
      last = (tick.bid + tick.ask) / 2.0;

   uchar payload[];
   PushU8(payload, 16);
   PushString(payload, NormalizeSymbol(symbol));
   PushU16(payload, ProtocolTimeframeCode(period));
   PushI64(payload, (long)tick.time);
   PushDouble(payload, tick.bid);
   PushDouble(payload, tick.ask);
   PushDouble(payload, last);
   PushDouble(payload, tick.volume_real > 0.0 ? tick.volume_real : (double)tick.volume);
   bool ok = SendPayload(payload);
   if(ok)
   {
      SentTicks++;
      if(TimeCurrent() != LastTickLog)
      {
         LastTickLog = TimeCurrent();
         Log(StringFormat("tick enviado #%I64u symbol=%s bid=%.5f ask=%.5f last=%.5f", SentTicks, NormalizeSymbol(symbol), tick.bid, tick.ask, last));
      }
   }
   return ok;
}

ushort ProtocolTimeframeCode(ENUM_TIMEFRAMES period)
{
   if(period == PERIOD_M1) return 1;
   if(period == PERIOD_M5) return 5;
   if(period == PERIOD_M15) return 15;
   if(period == PERIOD_M30) return 30;
   if(period == PERIOD_H1) return 60;
   if(period == PERIOD_H4) return 240;
   if(period == PERIOD_D1) return 1440;
   return (ushort)period;
}

ENUM_TIMEFRAMES PeriodFromProtocolCode(ushort code)
{
   if(code == 1) return PERIOD_M1;
   if(code == 5) return PERIOD_M5;
   if(code == 15) return PERIOD_M15;
   if(code == 30) return PERIOD_M30;
   if(code == 60) return PERIOD_H1;
   if(code == 240) return PERIOD_H4;
   if(code == 1440) return PERIOD_D1;
   return PERIOD_CURRENT;
}

bool SendCandleByShift(string symbol, ENUM_TIMEFRAMES period, int shift)
{
   datetime open_time = iTime(symbol, period, shift);
   if(open_time <= 0)
      return false;

   double open = iOpen(symbol, period, shift);
   double high = iHigh(symbol, period, shift);
   double low = iLow(symbol, period, shift);
   double close = iClose(symbol, period, shift);
   long tick_volume = iVolume(symbol, period, shift);
   if(open <= 0.0 || high <= 0.0 || low <= 0.0 || close <= 0.0)
      return false;

   uchar payload[];
   PushU8(payload, 4);
   PushString(payload, NormalizeSymbol(symbol));
   PushU16(payload, ProtocolTimeframeCode(period));
   PushI64(payload, (long)open_time);
   PushDouble(payload, open);
   PushDouble(payload, high);
   PushDouble(payload, low);
   PushDouble(payload, close);
   PushDouble(payload, (double)tick_volume);
   PushU32(payload, (uint)MathMax(tick_volume, 0));

   if(!SendPayload(payload))
      return false;

   SentCandles++;
   return true;
}

bool SendCurrentCandleSnapshot()
{
   bool ok = true;
   int total = ArraySize(MonitoredSymbols);
   for(int i = 0; i < total; i++)
   {
      if(!SendCandleByShift(MonitoredSymbols[i], _Period, 0))
         ok = false;
   }
   return ok;
}

bool SendAllSymbolTicks()
{
   bool ok = true;
   int total = ArraySize(MonitoredSymbols);
   for(int i = 0; i < total; i++)
   {
      MqlTick tick;
      if(!SymbolInfoTick(MonitoredSymbols[i], tick))
      {
         ok = false;
         continue;
      }

      if(tick.time <= 0 || tick.time == LastTickSentTimes[i])
         continue;

      LastTickSentTimes[i] = tick.time;
      if(!SendTick(MonitoredSymbols[i]))
         ok = false;
   }
   return ok;
}

int TargetHistoryBars()
{
   int period_seconds = PeriodSeconds(_Period);
   if(period_seconds <= 0)
      period_seconds = 60;

   int by_days = 0;
   if(InpHistoryDays > 0)
      by_days = (int)MathCeil((double)InpHistoryDays * 86400.0 / (double)period_seconds);

   int target = MathMax(InpHistoryBars, by_days);
   target = MathMax(target, InpMinHistoryBars);
   return MathMax(target, 1);
}

bool SendRecentCandles()
{
   int symbols_total = ArraySize(MonitoredSymbols);
   for(int symbol_index = 0; symbol_index < symbols_total; symbol_index++)
   {
      string symbol = MonitoredSymbols[symbol_index];
      int total = Bars(symbol, _Period);
      if(total <= 1)
      {
         Log(StringFormat("sem historico suficiente symbol=%s period=%d bars=%d", symbol, _Period, total));
         continue;
      }

      int count = MathMin(TargetHistoryBars(), total - 1);
      for(int shift = count; shift >= 1; shift--)
      {
         if(!SendCandleByShift(symbol, _Period, shift))
         {
            Log(StringFormat("SendCandle falhou symbol=%s shift=%d sent_candles=%I64u", NormalizeSymbol(symbol), shift, SentCandles));
            return false;
         }
      }
      Log(StringFormat("historico enviado candles=%d symbol=%s timeframe=%d", count, NormalizeSymbol(symbol), _Period));
   }
   return true;
}

void BeginRecentCandleSync()
{
   HistorySyncActive = false;
   HistorySyncDone = false;
   HistorySentInSession = 0;
   HistorySymbolIndex = 0;

   if(ArraySize(MonitoredSymbols) <= 0)
   {
      Log("sem simbolos monitorados para historico");
      HistorySyncDone = true;
      return;
   }

   while(HistorySymbolIndex < ArraySize(MonitoredSymbols))
   {
      string symbol = MonitoredSymbols[HistorySymbolIndex];
      int total = Bars(symbol, _Period);
      if(total > 1)
      {
         HistoryNextShift = MathMin(TargetHistoryBars(), total - 1);
         HistorySyncActive = HistoryNextShift > 0;
         Log(StringFormat("historico iniciado candles=%d symbol=%s timeframe=%d", HistoryNextShift, NormalizeSymbol(symbol), _Period));
         return;
      }
      Log(StringFormat("sem historico suficiente symbol=%s period=%d bars=%d", symbol, _Period, total));
      HistorySymbolIndex++;
   }

   HistorySyncDone = true;
}

bool SendRecentCandleBatch()
{
   if(!HistorySyncActive)
      return true;

   int batch_size = MathMax(InpHistoryBatchSize, 1);
   int sent_now = 0;
   while(HistorySymbolIndex < ArraySize(MonitoredSymbols) && sent_now < batch_size)
   {
      string symbol = MonitoredSymbols[HistorySymbolIndex];
      while(HistoryNextShift >= 1 && sent_now < batch_size)
      {
         if(!SendCandleByShift(symbol, _Period, HistoryNextShift))
         {
            Log(StringFormat("SendCandle falhou symbol=%s shift=%d sent_candles=%I64u", NormalizeSymbol(symbol), HistoryNextShift, SentCandles));
            return false;
         }
         HistoryNextShift--;
         HistorySentInSession++;
         sent_now++;
      }

      if(HistoryNextShift < 1)
      {
         Log(StringFormat("historico enviado ate agora=%d symbol=%s timeframe=%d", HistorySentInSession, NormalizeSymbol(symbol), _Period));
         HistorySymbolIndex++;
         if(HistorySymbolIndex < ArraySize(MonitoredSymbols))
         {
            string next_symbol = MonitoredSymbols[HistorySymbolIndex];
            int total = Bars(next_symbol, _Period);
            if(total > 1)
            {
               HistoryNextShift = MathMin(TargetHistoryBars(), total - 1);
               Log(StringFormat("historico iniciado candles=%d symbol=%s timeframe=%d", HistoryNextShift, NormalizeSymbol(next_symbol), _Period));
            }
            else
            {
               Log(StringFormat("sem historico suficiente symbol=%s period=%d bars=%d", next_symbol, _Period, total));
               HistoryNextShift = 0;
            }
         }
      }
   }

   if(HistorySymbolIndex >= ArraySize(MonitoredSymbols))
   {
      HistorySyncActive = false;
      HistorySyncDone = true;
      Log(StringFormat("historico multiativo enviado candles=%d symbols=%d timeframe=%d", HistorySentInSession, ArraySize(MonitoredSymbols), _Period));
   }

   return true;
}

void BeginOnDemandHistory(string requested_symbol, ushort timeframe_code, long from_time, uint limit)
{
   string symbol = ResolveBrokerSymbol(requested_symbol);
   ENUM_TIMEFRAMES period = PeriodFromProtocolCode(timeframe_code);
   if(symbol == "" || period == PERIOD_CURRENT)
   {
      Log(StringFormat("history request invalido symbol=%s tf=%d", requested_symbol, timeframe_code));
      return;
   }

   if(!SymbolSelect(symbol, true))
   {
      Log(StringFormat("SymbolSelect history request falhou symbol=%s err=%d", symbol, GetLastError()));
      return;
   }

   int total = Bars(symbol, period);
   if(total <= 1)
   {
      Log(StringFormat("sem historico para request symbol=%s timeframe=%d bars=%d", NormalizeSymbol(symbol), period, total));
      return;
   }

   DemandHistorySymbol = symbol;
   DemandHistoryPeriod = period;
   DemandHistoryFrom = from_time;
   DemandHistoryLimit = limit > 0 ? limit : 3000;
   DemandHistorySent = 0;
   DemandHistoryNextShift = total - 1;
   DemandHistoryActive = true;
   ActiveStreamSymbol = symbol;
   ActiveStreamPeriod = period;
   Log(StringFormat("history request iniciado symbol=%s timeframe=%d from=%I64d limit=%d bars=%d", NormalizeSymbol(symbol), period, from_time, DemandHistoryLimit, total));
}

bool SendOnDemandHistoryBatch()
{
   if(!DemandHistoryActive)
      return true;

   int batch_size = MathMax(InpHistoryBatchSize, 1);
   int sent_now = 0;
   while(DemandHistoryNextShift >= 1 && sent_now < batch_size && DemandHistorySent < DemandHistoryLimit)
   {
      datetime open_time = iTime(DemandHistorySymbol, DemandHistoryPeriod, DemandHistoryNextShift);
      if(open_time > 0 && (long)open_time > DemandHistoryFrom)
      {
         if(!SendCandleByShift(DemandHistorySymbol, DemandHistoryPeriod, DemandHistoryNextShift))
         {
            Log(StringFormat("history request SendCandle falhou symbol=%s shift=%d", NormalizeSymbol(DemandHistorySymbol), DemandHistoryNextShift));
            return false;
         }
         DemandHistorySent++;
         sent_now++;
      }
      DemandHistoryNextShift--;
   }

   if(DemandHistoryNextShift < 1 || DemandHistorySent >= DemandHistoryLimit)
   {
      Log(StringFormat("history request finalizado symbol=%s timeframe=%d sent=%d", NormalizeSymbol(DemandHistorySymbol), DemandHistoryPeriod, DemandHistorySent));
      DemandHistoryActive = false;
   }

   return true;
}

void ProcessInboundPayload(const uchar &payload[])
{
   if(ArraySize(payload) < 1)
      return;

   uchar message_type = payload[0];
   if(message_type != 17)
      return;

   int offset = 1;
   string symbol = ReadStringAt(payload, offset);
   if(offset + 14 > ArraySize(payload))
      return;
   ushort timeframe_code = ReadU16At(payload, offset);
   offset += 2;
   long from_time = ReadI64At(payload, offset);
   offset += 8;
   uint limit = ReadU32At(payload, offset);
   BeginOnDemandHistory(symbol, timeframe_code, from_time, limit);
}

void ReadInboundCommands()
{
   if(Socket == INVALID_HANDLE)
      return;

   uint readable = SocketIsReadable(Socket);
   if(readable > 0)
   {
      uchar chunk[];
      ArrayResize(chunk, (int)readable);
      int got = SocketRead(Socket, chunk, readable, 0);
      if(got > 0)
      {
         int old_size = ArraySize(InboundBuffer);
         ArrayResize(InboundBuffer, old_size + got);
         for(int i = 0; i < got; i++)
            InboundBuffer[old_size + i] = chunk[i];
      }
   }

   while(ArraySize(InboundBuffer) >= 16)
   {
      if(InboundBuffer[0] != 'F' || InboundBuffer[1] != 'U' || InboundBuffer[2] != 'S' ||
         InboundBuffer[3] != 'M' || InboundBuffer[4] != 'T' || InboundBuffer[5] != '5')
      {
         Log("frame inbound com magic invalido, limpando buffer");
         ArrayResize(InboundBuffer, 0);
         return;
      }

      ushort version = ReadU16At(InboundBuffer, 6);
      if(version != 1)
      {
         Log(StringFormat("frame inbound versao invalida=%d", version));
         ArrayResize(InboundBuffer, 0);
         return;
      }

      uint payload_len = ReadU32At(InboundBuffer, 8);
      uint checksum = ReadU32At(InboundBuffer, 12);
      int frame_len = 16 + (int)payload_len;
      if(ArraySize(InboundBuffer) < frame_len)
         return;

      uchar payload[];
      ArrayResize(payload, (int)payload_len);
      for(int i = 0; i < (int)payload_len; i++)
         payload[i] = InboundBuffer[16 + i];

      if(Crc32(payload) == checksum)
         ProcessInboundPayload(payload);
      else
         Log("frame inbound checksum invalido");

      RemoveInboundPrefix(frame_len);
   }
}

string NormalizeSymbol(string symbol)
{
   string s = symbol;
   StringToUpper(s);
   if(StringLen(s) >= 6)
   {
      string first6 = StringSubstr(s, 0, 6);
      bool letters = true;
      for(int i = 0; i < 6; i++)
      {
         ushort ch = StringGetCharacter(first6, i);
         if(ch < 'A' || ch > 'Z')
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

void AddMonitoredSymbol(string raw_symbol)
{
   string resolved = ResolveBrokerSymbol(raw_symbol);
   if(resolved == "")
      return;

   string normalized_raw = NormalizeSymbol(raw_symbol);
   if(normalized_raw == "AUS200" || NormalizeSymbol(resolved) == "AUS200")
      return;

   string normalized = NormalizeSymbol(resolved);
   int total = ArraySize(MonitoredSymbols);
   for(int i = 0; i < total; i++)
   {
      if(NormalizeSymbol(MonitoredSymbols[i]) == normalized)
         return;
   }

   if(!SymbolSelect(resolved, true))
   {
      Log(StringFormat("SymbolSelect falhou symbol=%s err=%d", resolved, GetLastError()));
      return;
   }

   ArrayResize(MonitoredSymbols, total + 1);
   ArrayResize(LastTickSentTimes, total + 1);
   MonitoredSymbols[total] = resolved;
   LastTickSentTimes[total] = 0;
}

string ResolveBrokerSymbol(string raw_symbol)
{
   string normalized = NormalizeSymbol(raw_symbol);
   if(normalized == "")
      return "";

   if(normalized == "XAUUSD")
      normalized = "GOLD";

   if(SymbolInfoInteger(normalized, SYMBOL_EXIST))
      return normalized;

   int selected_total = SymbolsTotal(true);
   for(int i = 0; i < selected_total; i++)
   {
      string candidate = SymbolName(i, true);
      if(NormalizeSymbol(candidate) == normalized)
         return candidate;
   }

   int all_total = SymbolsTotal(false);
   for(int j = 0; j < all_total; j++)
   {
      string candidate = SymbolName(j, false);
      if(NormalizeSymbol(candidate) == normalized)
         return candidate;
   }

   Log(StringFormat("simbolo nao encontrado no MT5 raw=%s normalized=%s", raw_symbol, normalized));
   return "";
}

void LoadSymbolsFromInput()
{
   string parts[];
   int count = StringSplit(InpSymbols, ',', parts);
   for(int i = 0; i < count; i++)
   {
      string item = parts[i];
      item = StringTrimLeft(item);
      item = StringTrimRight(item);
      if(item != "")
         AddMonitoredSymbol(item);
   }
}

void LoadSymbolsFromFusionCsv()
{
   if(!InpUseFusionSignalAssets)
      return;

   string file_name = "";
   long finder = FileFindFirst("fusion_signal_panel_*.csv", file_name, FILE_COMMON);
   if(finder == INVALID_HANDLE)
   {
      Log(StringFormat("nenhum CSV fusion_signal_panel_*.csv encontrado em Common Files err=%d", GetLastError()));
      return;
   }

   while(true)
   {
      string asset = file_name;
      StringReplace(asset, "fusion_signal_panel_", "");
      StringReplace(asset, ".csv", "");
      if(asset != "")
         AddMonitoredSymbol(asset);

      if(!FileFindNext(finder, file_name))
         break;
   }
   FileFindClose(finder);
}

void BuildMonitoredSymbols()
{
   ArrayResize(MonitoredSymbols, 0);
   ArrayResize(LastTickSentTimes, 0);
   AddMonitoredSymbol(_Symbol);
   LoadSymbolsFromInput();
   LoadSymbolsFromFusionCsv();

   string summary = "";
   int total = ArraySize(MonitoredSymbols);
   for(int i = 0; i < total; i++)
   {
      if(summary != "")
         summary += ",";
      summary += NormalizeSymbol(MonitoredSymbols[i]);
   }
   Log(StringFormat("ativos monitorados=%d [%s]", total, summary));
}

void Disconnect()
{
   if(Socket != INVALID_HANDLE)
   {
      SocketClose(Socket);
      Socket = INVALID_HANDLE;
   }
   HelloSent = false;
   HistorySyncActive = false;
   HistorySyncDone = false;
   HistoryNextShift = 0;
   HistorySentInSession = 0;
   HistorySymbolIndex = 0;
   DemandHistoryActive = false;
   DemandHistorySymbol = "";
   DemandHistoryFrom = 0;
   DemandHistoryLimit = 0;
   DemandHistorySent = 0;
   DemandHistoryNextShift = 0;
   ActiveStreamSymbol = "";
   ActiveStreamPeriod = PERIOD_CURRENT;
   ArrayResize(InboundBuffer, 0);
   HeartbeatFailCount = 0;
}

bool Connect()
{
   Disconnect();
   Log(StringFormat("conectando em %s:%d", InpHost, InpPort));
   Socket = SocketCreate();
   if(Socket == INVALID_HANDLE)
   {
      Log(StringFormat("SocketCreate falhou err=%d", GetLastError()));
      return false;
   }
   if(!SocketConnect(Socket, InpHost, InpPort, 1000))
   {
      Log(StringFormat("SocketConnect falhou err=%d", GetLastError()));
      Disconnect();
      return false;
   }
   Log("conectado, aguardando socket ficar gravavel");
   return true;
}

int OnInit()
{
   BuildMonitoredSymbols();
   EventSetTimer(1);
   WriteExecutionControl();
   Log(StringFormat("iniciado version=%s symbol=%s normalized=%s period=%d", FUSION_BRIDGE_VERSION, _Symbol, NormalizeSymbol(_Symbol), _Period));
   if(InpEnableSocketBridge)
      Connect();
   else
      Log("socket bridge desativado; modo snapshot-only ativo");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   Log(StringFormat("finalizado reason=%d ticks_enviados=%I64u", reason, SentTicks));
   EventKillTimer();
   if(InpEnableSocketBridge)
      Disconnect();
}

void OnTimer()
{
   WriteExecutionControl();
   ExportSnapshotFiles();

   if(!InpEnableSocketBridge)
      return;

   if(Socket == INVALID_HANDLE)
   {
      if(TimeCurrent() - LastConnectAttempt >= InpReconnectSeconds)
      {
         LastConnectAttempt = TimeCurrent();
         Connect();
      }
      return;
   }

   if(!HelloSent)
   {
      if(SendHello())
      {
         HelloSent = true;
         LastHeartbeat = TimeCurrent();
         HeartbeatFailCount = 0;
         Log("hello enviado");
         if(InpSendRecentCandles && InpAllowLegacyBulkHistory)
         {
            BeginRecentCandleSync();
            if(!SendRecentCandleBatch())
            {
               Log("SendRecentCandleBatch falhou, desconectando");
               Disconnect();
               return;
            }
         }
      }
      else
      {
         Log("SendHello falhou, desconectando");
         Disconnect();
      }
      return;
   }

   ReadInboundCommands();

   if(DemandHistoryActive)
   {
      if(!SendOnDemandHistoryBatch())
      {
         Log("SendOnDemandHistoryBatch falhou, desconectando");
         Disconnect();
      }
      return;
   }

   if(HistorySyncActive)
   {
      if(!SendRecentCandleBatch())
      {
         Log("SendRecentCandleBatch falhou, desconectando");
         Disconnect();
      }
      return;
   }

   if(InpSyncCurrentCandle && !HistorySyncActive && !HistorySyncDone)
      HistorySyncDone = true;

   if(InpSendHeartbeat && TimeCurrent() != LastHeartbeat)
   {
      LastHeartbeat = TimeCurrent();
      if(!SendHeartbeat())
      {
         HeartbeatFailCount++;
         Log(StringFormat("SendHeartbeat falhou count=%d", HeartbeatFailCount));
         if(HeartbeatFailCount >= 3)
         {
            Log("SendHeartbeat falhou 3x, desconectando");
            Disconnect();
            return;
         }
      }
      else
      {
         HeartbeatFailCount = 0;
      }
      if(Socket != INVALID_HANDLE && InpSendAllMonitoredTicks && !SendAllSymbolTicks())
      {
         Log("SendAllSymbolTicks falhou/parcial");
      }
      if(Socket != INVALID_HANDLE && InpOnlySendRequestedAsset && ActiveStreamSymbol != "")
      {
         if(!SendTickForPeriod(ActiveStreamSymbol, ActiveStreamPeriod != PERIOD_CURRENT ? ActiveStreamPeriod : _Period))
         {
            Log("SendTick ativo selecionado falhou/parcial");
         }
      }
      if(Socket != INVALID_HANDLE && InpSyncCurrentCandle && LastCurrentCandleSync != TimeCurrent())
      {
         LastCurrentCandleSync = TimeCurrent();
         bool current_ok = true;
         if(InpOnlySendRequestedAsset && ActiveStreamSymbol != "" && ActiveStreamPeriod != PERIOD_CURRENT)
            current_ok = SendCandleByShift(ActiveStreamSymbol, ActiveStreamPeriod, 0);
         else
            current_ok = SendCurrentCandleSnapshot();
         if(!current_ok)
         {
            Log("SendCurrentCandleSnapshot falhou, desconectando");
            Disconnect();
         }
         else
         {
            HeartbeatFailCount = 0;
         }
      }
   }
}

void OnTick()
{
   ExportSnapshotFiles();

   if(!InpEnableSocketBridge)
      return;

   if(Socket == INVALID_HANDLE)
      return;

   ReadInboundCommands();

   if(!HelloSent)
      return;
   if(HistorySyncActive)
      return;
   if(InpOnlySendRequestedAsset && ActiveStreamSymbol == "")
      return;

   string tick_symbol = InpOnlySendRequestedAsset && ActiveStreamSymbol != "" ? ActiveStreamSymbol : _Symbol;
   ENUM_TIMEFRAMES tick_period = InpOnlySendRequestedAsset && ActiveStreamPeriod != PERIOD_CURRENT ? ActiveStreamPeriod : _Period;
   if(!SendTickForPeriod(tick_symbol, tick_period))
   {
      Log("SendTick falhou, desconectando");
      Disconnect();
      return;
   }
   if(InpSyncCurrentCandle && LastCurrentCandleSync != TimeCurrent())
   {
      LastCurrentCandleSync = TimeCurrent();
      bool current_ok = true;
      if(InpOnlySendRequestedAsset && ActiveStreamSymbol != "" && ActiveStreamPeriod != PERIOD_CURRENT)
         current_ok = SendCandleByShift(ActiveStreamSymbol, ActiveStreamPeriod, 0);
      else
         current_ok = SendCurrentCandleSnapshot();
      if(!current_ok)
      {
         Log("SendCurrentCandleSnapshot falhou, desconectando");
         Disconnect();
      }
   }
}
