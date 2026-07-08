import React, { useState } from 'react';
import { fusionLocalClient } from '@/api/fusionLocalClient';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Link } from 'react-router-dom';
import { Loader2, Mail, ArrowLeft } from 'lucide-react';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try { await fusionLocalClient.auth.resetPasswordRequest(email); } catch {}
    setSent(true);
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm bg-card border-border">
        <CardHeader className="text-center space-y-2">
          <CardTitle className="text-xl font-heading">Recuperar Senha</CardTitle>
          <CardDescription className="text-xs">
            {sent ? 'Verifique seu email' : 'Insira seu email para receber o link de recuperaÃ§Ã£o'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {sent ? (
            <div className="text-center space-y-3">
              <p className="text-sm text-muted-foreground">Se o email existir, vocÃª receberÃ¡ um link para redefinir sua senha.</p>
              <Link to="/login"><Button variant="outline" className="w-full h-9 text-sm"><ArrowLeft className="w-4 h-4 mr-2" />Voltar ao Login</Button></Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-3">
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
                  <Input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="seu@email.com" className="pl-9 h-9 text-sm bg-muted border-border" required />
                </div>
              </div>
              <Button type="submit" disabled={loading} className="w-full h-9 text-sm">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Enviar Link'}
              </Button>
              <Link to="/login" className="block text-center text-xs text-primary hover:underline">Voltar ao Login</Link>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
