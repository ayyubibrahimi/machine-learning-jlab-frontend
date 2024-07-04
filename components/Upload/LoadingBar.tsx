import React from 'react';
import styles from './LoadingBar.module.scss';

interface LoadingBarProps {
  isLoading: boolean;
}

const LoadingBar: React.FC<LoadingBarProps> = ({ isLoading }) => {
  return (
    <div className={`${styles.loadingBarContainer} ${isLoading ? styles.isLoading : ''}`}>
      {isLoading && <div className={styles.loadingBar} />}
    </div>
  );
};

export default LoadingBar;