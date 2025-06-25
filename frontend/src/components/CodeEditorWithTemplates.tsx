'use client'

import React, { useState, useEffect } from 'react';
import { CodeEditor } from './CodeEditor';
import { codeTemplates, getTemplatesByCategory } from '../../src/data/codeTemplates';

interface CodeEditorWithTemplatesProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  loading?: boolean;
}

export const CodeEditorWithTemplates: React.FC<CodeEditorWithTemplatesProps> = ({
  value,
  onChange,
  onSubmit,
  loading = false,
}) => {
  const [showTemplates, setShowTemplates] = useState(false);
  const [recentCodes, setRecentCodes] = useState<Array<{ code: string; timestamp: string }>>([]);

  useEffect(() => {
    // Load recent codes from localStorage
    const savedRecent = localStorage.getItem('crucible-recent-codes');
    if (savedRecent) {
      try {
        setRecentCodes(JSON.parse(savedRecent));
      } catch (e) {
        console.error('Failed to parse recent codes:', e);
      }
    }

    // Load last saved draft
    const draft = localStorage.getItem('crucible-draft-code');
    if (draft && !value) {
      onChange(draft);
    }
  }, []);

  const handleTemplateSelect = (templateId: string) => {
    const template = codeTemplates.find(t => t.id === templateId);
    if (template) {
      onChange(template.code);
      setShowTemplates(false);
    }
  };

  const handleSubmit = () => {
    // Save to recent codes
    const newRecent = [
      { code: value, timestamp: new Date().toISOString() },
      ...recentCodes.filter(r => r.code !== value).slice(0, 9) // Keep last 10 unique
    ];
    setRecentCodes(newRecent);
    localStorage.setItem('crucible-recent-codes', JSON.stringify(newRecent));
    
    onSubmit();
  };

  const loadRecentCode = (code: string) => {
    onChange(code);
    setShowTemplates(false);
  };

  const templateCategories = getTemplatesByCategory();

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Code Editor</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setShowTemplates(!showTemplates)}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
          >
            {showTemplates ? 'Hide Templates' : 'Show Templates'}
          </button>
          {value && (
            <button
              onClick={() => {
                localStorage.setItem('crucible-last-code', value);
                localStorage.setItem('crucible-last-saved', new Date().toISOString());
              }}
              className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 transition-colors"
              title="Save (Ctrl+S)"
            >
              💾 Save
            </button>
          )}
        </div>
      </div>

      {/* Templates Panel */}
      {showTemplates && (
        <div className="mb-4 border border-gray-200 rounded-lg p-4 bg-gray-50">
          <h3 className="font-medium text-gray-900 mb-3">Code Templates</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Array.from(templateCategories.entries()).map(([category, templates]) => (
              <div key={category}>
                <h4 className="text-sm font-medium text-gray-700 mb-2">{category}</h4>
                <div className="space-y-1">
                  {templates.map(template => (
                    <button
                      key={template.id}
                      onClick={() => handleTemplateSelect(template.id)}
                      className="w-full text-left px-3 py-2 text-sm rounded hover:bg-white hover:shadow-sm transition-all"
                    >
                      <div className="font-medium">{template.name}</div>
                      <div className="text-xs text-gray-600">{template.description}</div>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Recent Submissions */}
          {recentCodes.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Recent Submissions</h4>
              <div className="space-y-1">
                {recentCodes.slice(0, 3).map((recent, idx) => (
                  <button
                    key={idx}
                    onClick={() => loadRecentCode(recent.code)}
                    className="w-full text-left px-3 py-2 text-sm rounded hover:bg-white hover:shadow-sm transition-all"
                  >
                    <div className="font-mono text-xs truncate">{recent.code.split('\n')[0]}</div>
                    <div className="text-xs text-gray-500">
                      {new Date(recent.timestamp).toLocaleString()}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Code Editor */}
      <CodeEditor
        value={value}
        onChange={onChange}
        height="400px"
      />

      {/* Action Buttons */}
      <div className="mt-4 flex gap-3">
        <button
          onClick={handleSubmit}
          disabled={loading || !value.trim()}
          className="px-6 py-2.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
        >
          {loading ? 'Evaluating...' : 'Run Evaluation'}
        </button>
        
        <button
          onClick={() => onChange('')}
          disabled={loading || !value}
          className="px-4 py-2.5 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Clear
        </button>

        <div className="ml-auto text-sm text-gray-500 flex items-center">
          <kbd className="px-2 py-1 bg-gray-100 border border-gray-300 rounded text-xs">Ctrl</kbd>
          <span className="mx-1">+</span>
          <kbd className="px-2 py-1 bg-gray-100 border border-gray-300 rounded text-xs">S</kbd>
          <span className="ml-2">to save</span>
        </div>
      </div>
    </div>
  );
};