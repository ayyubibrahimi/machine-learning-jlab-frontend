import React, { useState } from 'react';
import styles from './Sidebar.module.scss';
import { SavedResponse, SentencePagePair } from './UploadInterface';

interface SidebarProps {
  onPageClick: (pageNumber: number, filename: string) => void;
  sentencePagePairs: SentencePagePair[];
  onSavedResponseClick: (response: SavedResponse) => void;
  savedResponses: SavedResponse[];
  onDeleteSavedResponse: (responseId: number) => void;
  onRenameSavedResponse: (responseId: number, newLabel: string) => void;
  onSaveOutput: (content: any) => void;
  lastUploadedData: any;
}

const Sidebar: React.FC<SidebarProps> = ({
  onPageClick,
  sentencePagePairs,
  onSavedResponseClick,
  savedResponses,
  onDeleteSavedResponse,
  onRenameSavedResponse,
  onSaveOutput,
  lastUploadedData,
}) => {
  const [editingResponseId, setEditingResponseId] = useState<number | null>(null);
  const [newLabel, setNewLabel] = useState<string>('');

  const handleRenameClick = (responseId: number) => {
    setEditingResponseId(responseId);
    const response = savedResponses.find((resp) => resp.id === responseId);
    if (response) {
      setNewLabel(response.label);
    }
  };

  const handleRenameSubmit = (responseId: number) => {
    onRenameSavedResponse(responseId, newLabel);
    setEditingResponseId(null);
    setNewLabel('');
  };

  return (
    <div className={styles.sidebar}>
      <h3>Workspace</h3>
      <div className={styles.savedResponsesContainer}>
        <button
          onClick={() => onSaveOutput(lastUploadedData)}
          disabled={!lastUploadedData}
          className={styles.saveResponseButton}
        >
          Save Response
        </button>
        <div className={styles.savedResponses}>
          {savedResponses.map((response) => (
            <div key={response.id} className={styles.savedResponse}>
              {editingResponseId === response.id ? (
                <div>
                  <input
                    type="text"
                    value={newLabel}
                    onChange={(e) => setNewLabel(e.target.value)}
                    className={styles.renameInput}
                  />
                  <button
                    onClick={() => handleRenameSubmit(response.id)}
                    className={styles.renameButton}
                  >
                    Save
                  </button>
                </div>
              ) : (
                <div>
                  <button
                    onClick={() => onSavedResponseClick(response)}
                    className={styles.responseLabel}
                  >
                    {response.label}
                  </button>
                  <div className={styles.responseButtons}>
                    <button onClick={() => handleRenameClick(response.id)}>Rename</button>
                    <button onClick={() => onDeleteSavedResponse(response.id)}>Delete</button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Sidebar;