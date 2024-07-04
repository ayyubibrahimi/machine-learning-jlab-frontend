import React from 'react';
import UploadInterface from '../components/Upload/UploadInterface';
import styles from '../styles/Home.module.scss';

export default function Home() {
  return (
    <div className={`flex flex-col min-h-screen ${styles.container}`}>
      <div className="flex-grow relative">
        <div className="absolute inset-0 flex items-center justify-center">
          <UploadInterface />
        </div>
      </div>
    </div>
  );
}