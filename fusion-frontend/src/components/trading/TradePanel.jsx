import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { fusionLocalClient } from '@/api/fusionLocalClient';
import { ArrowUpCircle, ArrowDownCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function TradePanel({ symbol, currentPrice }) {
  const [lotSize, setLotSize] = useState('0.01');
  const [stopLoss, setStopLoss] = useState('');
  const [takeProfit, setTakeProfit] = useState('');
  const [orderType, setOrderType] = useState('market');
  const [limitPrice, setLimitPrice] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleTrade = async (type) => {
    setIsSubmitting(true);
    const tradeData = {
      symbol,
      type,
      entry_price: orderType === 'market' ? currentPrice : parseFloat(limitPrice),
      lot_size: parseFloat(lotSize),
      status: orderType === 'market' ? 'open' : 'pending',
      opened_at: new Date().toISOString(),
    };
    if (stopLoss) tradeData.stop_loss = parseFloat(stopLoss);
    if (takeProfit) tradeData.take_profit = parseFloat(takeProfit);

    await fusionLocalClient.entities.Trade.create(tradeData);
    setIsSubmitting(false);
  };

  return (
    <div className="w-full border-l border-border bg-card flex flex-col">
      <div className="px-4 py-3 border-b border-border">
        <h3 className="text-sm font-semibold font-heading">Nova Ordem</h3>
        <p className="text-xs text-muted-foreground font-mono mt-0.5">{symbol}</p>
      </div>

      <Tabs defaultValue="market" onValueChange={setOrderType} className="flex-1 flex flex-col">
        <TabsList className="mx-4 mt-3 bg-muted">
          <TabsTrigger value="market" className="text-xs flex-1">Mercado</TabsTrigger>
          <TabsTrigger value="limit" className="text-xs flex-1">Limite</TabsTrigger>
        </TabsList>

        <div className="p-4 space-y-3 flex-1">
          <TabsContent value="limit" className="mt-0">
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">PreÃ§o</Label>
              <Input
                type="number"
                step="0.00001"
                value={limitPrice}
                onChange={e => setLimitPrice(e.target.value)}
                placeholder="0.00000"
                className="h-8 text-xs font-mono bg-muted border-border"
              />
            </div>
          </TabsContent>

          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Volume (lotes)</Label>
            <Input
              type="number"
              step="0.01"
              min="0.01"
              value={lotSize}
              onChange={e => setLotSize(e.target.value)}
              className="h-8 text-xs font-mono bg-muted border-border"
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Stop Loss</Label>
            <Input
              type="number"
              step="0.00001"
              value={stopLoss}
              onChange={e => setStopLoss(e.target.value)}
              placeholder="Opcional"
              className="h-8 text-xs font-mono bg-muted border-border"
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Take Profit</Label>
            <Input
              type="number"
              step="0.00001"
              value={takeProfit}
              onChange={e => setTakeProfit(e.target.value)}
              placeholder="Opcional"
              className="h-8 text-xs font-mono bg-muted border-border"
            />
          </div>

          <div className="text-center py-2">
            <span className="text-xs text-muted-foreground">PreÃ§o atual</span>
            <p className="text-lg font-mono font-bold">{currentPrice?.toFixed(5) || 'â€”'}</p>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <Button
              onClick={() => handleTrade('BUY')}
              disabled={isSubmitting}
              className="h-10 bg-green-600 hover:bg-green-700 text-white font-semibold text-sm"
            >
              <ArrowUpCircle className="w-4 h-4 mr-1.5" />
              Comprar
            </Button>
            <Button
              onClick={() => handleTrade('SELL')}
              disabled={isSubmitting}
              className="h-10 bg-red-600 hover:bg-red-700 text-white font-semibold text-sm"
            >
              <ArrowDownCircle className="w-4 h-4 mr-1.5" />
              Vender
            </Button>
          </div>
        </div>
      </Tabs>
    </div>
  );
}
