import React, { useState } from 'react';
import { base44 } from '@/api/base44Client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Link } from 'react-router-dom';
import { Loader2, Mail, Lock, TrendingUp, KeyRound } from 'lucide-react';

export default function Register() {
  const [step, setStep] = useState('register');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    if (password !== confirmPassword) { setError('As senhas não coincidem'); return; }
    setLoading(true);
    try {
      await base44.auth.register({ email, password });
      setStep('otp');
    } catch (err) {
      setError(err.message || 'Erro ao registrar');
    }
    setLoading(false);
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await base44.auth.verifyOtp({ email, otpCode });
      base44.auth.setToken(res.access_token);
      window.location.href = '/';
    } catch (err) {
      setError(err.message || 'Código inválido');
    }
    setLoading(false);
  };

  const handleResend = async () => {
    await base44.auth.resendOtp(email);
  };

  const handleGoogle = () => {
    base44.auth.loginWithProvider('google', '/');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm bg-card border-border">
        <CardHeader className="text-center space-y-2">
          <div className="mx-auto w-12 h-12 rounded-xl bg-primary flex items-center justify-center mb-2">
            <TrendingUp className="w-6 h-6 text-primary-foreground" />
          </div>
          <CardTitle className="text-xl font-heading">Criar Conta</CardTitle>
          <CardDescription className="text-xs">
            {step === 'register' ? 'Preencha os dados abaixo' : 'Verifique seu email'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {step === 'register' ? (
            <>
              <form onSubmit={handleRegister} className="space-y-3">
                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">Email</Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
                    <Input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="seu@email.com" className="pl-9 h-9 text-sm bg-muted border-border" required />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">Senha</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
                    <Input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" className="pl-9 h-9 text-sm bg-muted border-border" required />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">Confirmar Senha</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
                    <Input type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} placeholder="••••••••" className="pl-9 h-9 text-sm bg-muted border-border" required />
                  </div>
                </div>
                {error && <p className="text-xs text-destructive">{error}</p>}
                <Button type="submit" disabled={loading} className="w-full h-9 text-sm">
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Criar Conta'}
                </Button>
              </form>
              <div className="relative">
                <div className="absolute inset-0 flex items-center"><span className="w-full border-t border-border" /></div>
                <div className="relative flex justify-center text-xs"><span className="bg-card px-2 text-muted-foreground">ou</span></div>
              </div>
              <Button variant="outline" onClick={handleGoogle} className="w-full h-9 text-sm border-border">Continuar com Google</Button>
            </>
          ) : (
            <form onSubmit={handleVerifyOtp} className="space-y-3">
              <p className="text-xs text-muted-foreground text-center">Enviamos um código para <strong>{email}</strong></p>
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Código de Verificação</Label>
                <div className="relative">
                  <KeyRound className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
                  <Input value={otpCode} onChange={e => setOtpCode(e.target.value)} placeholder="000000" className="pl-9 h-9 text-sm font-mono bg-muted border-border text-center tracking-widest" required />
                </div>
              </div>
              {error && <p className="text-xs text-destructive">{error}</p>}
              <Button type="submit" disabled={loading} className="w-full h-9 text-sm">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Verificar'}
              </Button>
              <button type="button" onClick={handleResend} className="w-full text-xs text-primary hover:underline">Reenviar código</button>
            </form>
          )}
          <p className="text-xs text-center text-muted-foreground">
            Já tem conta? <Link to="/login" className="text-primary hover:underline">Entrar</Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}