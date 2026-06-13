export interface QuestionInputProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export default function QuestionInput({ value, onChange, disabled }: QuestionInputProps) {
  return (
    <div>
      <label className="mb-space-1 block text-small text-text-secondary">問題（可選）</label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        rows={3}
        placeholder="想了解什麼？（可留空，AI 將提供一般性解讀）"
        className="w-full rounded-sm border border-border-subtle bg-bg-inset px-space-2 py-1 text-body text-text-primary focus:border-accent-primary focus:outline-none disabled:opacity-50"
      />
    </div>
  );
}
