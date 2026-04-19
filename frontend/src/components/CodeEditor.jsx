import React, { useState } from 'react';
import Editor from '@monaco-editor/react';
import { Send, Loader2 } from 'lucide-react';

const LANGUAGES = [
  { value: 'python', label: 'Python' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'java', label: 'Java' },
  { value: 'cpp', label: 'C++' },
  { value: 'go', label: 'Go' },
  { value: 'rust', label: 'Rust' },
];

const CodeEditor = ({ starterCode = '', onSubmit, disabled, onChange, onLanguageChange }) => {
  const [code, setCode] = useState(starterCode);
  const [language, setLanguage] = useState('python');


  React.useEffect(() => {
    window.currentCode = code;
    if (onChange) onChange(code);
  }, [code]);

  React.useEffect(() => {
    window.currentLanguage = language;
    if (onLanguageChange) onLanguageChange(language);
  }, [language]);

  const handleSubmit = () => {
    if (!code.trim() || disabled) return;
    onSubmit(code, language);
  };

  return (
    <div className="code-editor-container glass-card">
      <div className="code-editor-toolbar">
        <select
          className="language-select"
          value={language}
          onChange={e => setLanguage(e.target.value)}
          disabled={disabled}
        >
          {LANGUAGES.map(lang => (
            <option key={lang.value} value={lang.value}>{lang.label}</option>
          ))}
        </select>
        <button
          className="btn-primary"
          onClick={handleSubmit}
          disabled={disabled || !code.trim()}
        >
          {disabled
            ? <><Loader2 size={16} className="animate-spin" /> Evaluating...</>
            : <><Send size={16} /> Submit Code</>}
        </button>
      </div>
      <Editor
        height="380px"
        language={language}
        value={code}
        onChange={val => setCode(val || '')}
        theme="vs-dark"
        options={{
          fontSize: 14,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          readOnly: disabled,
          wordWrap: 'on',
        }}
      />
    </div>
  );
};

export default CodeEditor;
