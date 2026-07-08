import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Upload, Database, FileJson, Loader2 } from 'lucide-react';
import { fusionLocalClient } from '@/api/fusionLocalClient';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';

export default function MT5DataImporter({ symbol, timeframe, onImported }) {
  const [open, setOpen] = useState(false);
  const [jsonData, setJsonData] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleJsonImport = async () => {
    setIsLoading(true);
    const parsed = JSON.parse(jsonData);
    const candlesData = Array.isArray(parsed) ? parsed : [parsed];
    const formatted = candlesData.map(c => ({
      symbol,
      timeframe,
      open: c.open || c.Open || c.o,
      high: c.high || c.High || c.h,
      low: c.low || c.Low || c.l,
      close: c.close || c.Close || c.c,
      volume: c.volume || c.Volume || c.v || 0,
      timestamp: c.timestamp || c.time || c.Time || c.date || c.Date || new Date().toISOString(),
    }));
    await fusionLocalClient.entities.Candle.bulkCreate(formatted);
    setIsLoading(false);
    setOpen(false);
    onImported?.();
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setIsLoading(true);

    const { file_url } = await fusionLocalClient.integrations.Core.UploadFile({ file });
    const result = await fusionLocalClient.integrations.Core.ExtractDataFromUploadedFile({
      file_url,
      json_schema: {
        type: "object",
        properties: {
          candles: {
            type: "array",
            items: {
              type: "object",
              properties: {
                open: { type: "number" },
                high: { type: "number" },
                low: { type: "number" },
                close: { type: "number" },
                volume: { type: "number" },
                timestamp: { type: "string" }
              }
            }
          }
        }
      }
    });

    if (result.status === 'success' && result.output?.candles) {
      const formatted = result.output.candles.map(c => ({
        symbol,
        timeframe,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
        volume: c.volume || 0,
        timestamp: c.timestamp || new Date().toISOString(),
      }));
      await fusionLocalClient.entities.Candle.bulkCreate(formatted);
    }

    setIsLoading(false);
    setOpen(false);
    onImported?.();
  };

  const generateSampleData = async () => {
    setIsLoading(true);
    const candles = [];
    let price = symbol.includes('JPY') ? 150.000 : symbol.includes('XAU') ? 2350.00 : symbol.includes('BTC') ? 67000 : 1.08500;
    const now = new Date();
    const minutesMap = { M1: 1, M5: 5, M15: 15, M30: 30, H1: 60, H4: 240, D1: 1440 };
    const interval = minutesMap[timeframe] || 5;

    for (let i = 200; i >= 0; i--) {
      const timestamp = new Date(now.getTime() - i * interval * 60000);
      const volatility = price * 0.001;
      const open = price;
      const change = (Math.random() - 0.48) * volatility;
      const high = open + Math.abs(change) + Math.random() * volatility * 0.5;
      const low = open - Math.abs(change) - Math.random() * volatility * 0.5;
      const close = open + change;
      price = close;

      candles.push({
        symbol,
        timeframe,
        open: parseFloat(open.toFixed(5)),
        high: parseFloat(high.toFixed(5)),
        low: parseFloat(low.toFixed(5)),
        close: parseFloat(close.toFixed(5)),
        volume: Math.floor(Math.random() * 5000 + 500),
        timestamp: timestamp.toISOString(),
      });
    }

    // Bulk create in batches
    for (let i = 0; i < candles.length; i += 50) {
      await fusionLocalClient.entities.Candle.bulkCreate(candles.slice(i, i + 50));
    }

    setIsLoading(false);
    setOpen(false);
    onImported?.();
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="text-xs gap-1.5 text-muted-foreground hover:text-foreground">
          <Database className="w-3.5 h-3.5" />
          Importar Dados
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md bg-card border-border">
        <DialogHeader>
          <DialogTitle className="font-heading">Importar Dados MT5</DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="sample">
          <TabsList className="w-full bg-muted">
            <TabsTrigger value="sample" className="text-xs flex-1">Demo</TabsTrigger>
            <TabsTrigger value="json" className="text-xs flex-1">JSON</TabsTrigger>
            <TabsTrigger value="file" className="text-xs flex-1">Arquivo</TabsTrigger>
          </TabsList>

          <TabsContent value="sample" className="mt-4 space-y-3">
            <p className="text-xs text-muted-foreground">
              Gera 200 candles de exemplo para {symbol} ({timeframe}) para testar o grÃ¡fico.
            </p>
            <Button onClick={generateSampleData} disabled={isLoading} className="w-full">
              {isLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Database className="w-4 h-4 mr-2" />}
              Gerar Dados Demo
            </Button>
          </TabsContent>

          <TabsContent value="json" className="mt-4 space-y-3">
            <Label className="text-xs text-muted-foreground">
              Cole os dados JSON exportados do MT5 (array de objetos com open, high, low, close, volume, timestamp)
            </Label>
            <Textarea
              value={jsonData}
              onChange={e => setJsonData(e.target.value)}
              placeholder='[{"open":1.085,"high":1.086,...}]'
              className="h-40 text-xs font-mono bg-muted border-border"
            />
            <Button onClick={handleJsonImport} disabled={isLoading || !jsonData} className="w-full">
              {isLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileJson className="w-4 h-4 mr-2" />}
              Importar JSON
            </Button>
          </TabsContent>

          <TabsContent value="file" className="mt-4 space-y-3">
            <Label className="text-xs text-muted-foreground">
              Upload arquivo CSV ou Excel exportado do MT5
            </Label>
            <Input
              type="file"
              accept=".csv,.xlsx,.json"
              onChange={handleFileUpload}
              disabled={isLoading}
              className="text-xs bg-muted border-border"
            />
            {isLoading && (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-5 h-5 animate-spin text-primary" />
                <span className="ml-2 text-xs text-muted-foreground">Processando...</span>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
