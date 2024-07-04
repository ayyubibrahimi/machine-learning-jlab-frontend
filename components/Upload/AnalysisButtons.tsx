import React from 'react';
import classNames from 'classnames';
import styles from './AnalysisButtons.module.scss';

interface AnalysisButtonsProps {
  selectedAnalysis: 'process-detailed.py'  | 'process-brief.py' | null;
  onAnalysisClick: (analysis: 'process-detailed.py' | 'process-brief.py') => void;
}

const AnalysisButtons: React.FC<AnalysisButtonsProps> = ({ selectedAnalysis, onAnalysisClick }) => {
  return (
    <div className={styles.analysisButtonsContainer}>
      <button
        className={classNames(styles.analysisButton, selectedAnalysis === 'process-detailed.py' && styles.selected)}
        onClick={() => onAnalysisClick('process-detailed.py')}
      >
        Generate Detailed Summary
      </button>
      <button
        className={classNames(styles.analysisButton, selectedAnalysis === 'process-brief.py' && styles.selected)}
        onClick={() => onAnalysisClick('process-brief.py')}
      >
        Generate Brief Summary
      </button>
    </div>
  );
};

export default AnalysisButtons;