import React from 'react';
import styles from './ScriptDropdown.module.scss';

interface ScriptDropdownProps {
  selectedScript: 'process-detailed.py' | 'process-brief.py' | 'timelines.py' |'process-comprehensive.py';
  onScriptChange: (script: 'process-detailed.py' |  'process-brief.py' |'timelines.py' |'process-comprehensive.py') => void;
}

const ScriptDropdown: React.FC<ScriptDropdownProps> = ({ selectedScript, onScriptChange }) => {
  return (
    <div className={styles.scriptDropdown}>
      <select
        value={selectedScript}
        onChange={(e) => onScriptChange(e.target.value as 'process-detailed.py' |  'process-brief.py' | 'timelines.py' |'process-comprehensive.py')}
        className={styles.scriptSelect}
      >
        <option value="process-detailed.py">Generate Detailed Summary</option>
        <option value="process-brief.py">Generate Brief Summary</option>
        <option value="process-comprehensive.py">Generate Comprehensive Summary</option>
        <option value="timelines.py">Generate a Timeline of Events</option>
      </select>
    </div>
  );
};

export default ScriptDropdown;