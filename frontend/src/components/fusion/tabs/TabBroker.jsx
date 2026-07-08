import { Field, Toggle, NumInput, TextInput, Section } from '../FusionFieldRenderers';

export default function TabBroker({ draft, set }) {
  const b = draft.broker || {};
  const upd = (k, v) => set('broker', { ...b, [k]: v });

  return (
    <div className="space-y-2">
      <Section title="Configuração MT5">
        <Field label="terminal_path">
          <TextInput value={b.terminal_path} onChange={v => upd('terminal_path', v)} wide />
        </Field>
        <Field label="login">
          <NumInput value={b.login} onChange={v => upd('login', v)} step={1} />
        </Field>
        <Field label="password">
          <TextInput value={b.password} onChange={v => upd('password', v)} type="password" />
        </Field>
        <Field label="server">
          <TextInput value={b.server} onChange={v => upd('server', v)} />
        </Field>
        <Field label="startup_timeout" unit="s">
          <NumInput value={b.startup_timeout} onChange={v => upd('startup_timeout', v)} step={1} unit="s" small />
        </Field>
      </Section>
    </div>
  );
}