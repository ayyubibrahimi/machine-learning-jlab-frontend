import React, { useState } from 'react';
import styles from './Fileupload.module.scss';

interface FileUploadProps {
  onFileUpload: (files: File[]) => Promise<any>;
  onSummaryDescriptionChange: (description: string) => void;
  disabled?: boolean;
  multiple?: boolean;
  onClearScreen: () => void;
  onFilesSelected: () => void;
}

const FileUpload: React.FC<FileUploadProps> = ({
  onFileUpload,
  onSummaryDescriptionChange,
  disabled,
  multiple,
  onClearScreen,
  onFilesSelected
}) => {
  const [files, setFiles] = useState<File[]>([]);
  const [summaryDescription, setSummaryDescription] = useState('');

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = event.target.files;
    if (selectedFiles) {
      setFiles(Array.from(selectedFiles));
      onClearScreen();
      onFilesSelected();
    }
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (files.length === 0) {
      alert('Please select one or more PDF files to upload.');
      return;
    }
    onClearScreen();
    onFileUpload(files).catch(error => {
      console.error('Upload failed:', error);
    });
  };

  const handleDescriptionChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSummaryDescription(event.target.value);
    onSummaryDescriptionChange(event.target.value);
  };

  return (
    <form onSubmit={handleSubmit} className={styles.uploadForm}>
      <div className={styles.uploadInputContainer}>
        <input
          type="text"
          placeholder="Describe what to include in the summary"
          value={summaryDescription}
          onChange={handleDescriptionChange}
          className={styles.summaryInput}
        />
        <input
          type="file"
          accept=".pdf, .jpeg, .jpg, .png"
          onChange={handleFileChange}
          className={styles.fileInput}
          id="fileInput"
          multiple={multiple}
          disabled={disabled}
        />
        <label htmlFor="fileInput" className={styles.fileInputLabel} aria-label="Select files">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </label>
        <button type="submit" disabled={disabled} className={styles.processButton} aria-label="Process files">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 4L12 20M12 4L6 10M12 4L18 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>
    </form>
  );
};

export default FileUpload;