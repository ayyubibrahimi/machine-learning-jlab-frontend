import React from 'react';
import styles from './ModelDropdown.module.scss';

interface ModelDropdownProps {
  selectedModel: string;
  onModelChange: (model: string) => void;
}

const ModelDropdown: React.FC<ModelDropdownProps> = ({ selectedModel, onModelChange }) => {
  return (
    <div className={styles.modelDropdown}>
      <select
        value={selectedModel}
        onChange={(e) => onModelChange(e.target.value)}
        className={styles.modelSelect}
      >
        <option value="">Select Model</option>
        <option value="gpt-3.5-0125">GPT-3.5-Turbo</option>
        <option value="claude-3-haiku-20240307">Claude-3-Haiku</option>
      </select>
    </div>
  );
};

export default ModelDropdown;