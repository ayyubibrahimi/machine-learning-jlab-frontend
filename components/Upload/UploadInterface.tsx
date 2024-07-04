'use client';


import React, { useState, useRef, useEffect, useCallback  } from 'react';
import FileUpload from './FileUpload';
import styles from './UploadInterface.module.scss';
import Sidebar from './Sidebar';
import { db } from './FirebaseClient'; // Import the initialized Firestore instance
import { collection, getDocs, query, where } from 'firebase/firestore';
import { saveAs } from 'file-saver';
import LoadingBar from './LoadingBar'; // Import the LoadingBar component
import AboutContent from './AboutContent';
import Modal from 'react-modal';
import {ArrowUp,  ArrowLeft, ArrowRight, X , Plus } from 'lucide-react';
import EmailCard from './EmailCard';

import Image from 'next/image';


export interface SentencePagePair {
  filename: string;
  sentence: string;
  start_page?: number; // Optional for process-detailed.py, process-brief.py, process-comprehensive.py
  end_page?: number; // Optional for process-detailed.py, process-brief.py, process-comprehensive.py
  page_numbers?: string[]; // Optional for timelines.py
}


export interface DisplayedContent {
  groupedSentencePagePairs: Record<string, SentencePagePair[]>;
}

interface UploadedFilePath {
  id: number;
  filename: string;
  pdfFileUrl: string;
}

export type SavedResponse = {
  id: number;
  label: string;
  script: "process-detailed.py" | "process-brief.py" | 'process-comprehensive.py' | 'timelines.py'; // Ensure correct spelling
  content: DisplayedContent | null;
  pdfUrls: { id: number; filename: string; pdfFileUrl: string; }[];
  renderedOutput: string;
};


interface ProcessedDataItem {
  files: {
    filename: string;
    sentence: string;
    start_page?: number; // Optional for process-detailed.py, process-brief.py, process-comprehensive.py
    end_page?: number; // Optional for process-detailed.py, process-brief.py, process-comprehensive.py
    page_numbers?: string[]; // Optional for timelines.py
  }[];
}


const UploadInterface: React.FC = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [processingStatus, setProcessingStatus] = useState<'idle' | 'processing' | 'complete'>('idle');
  const [sentencePagePairs, setSentencePagePairs] = useState<SentencePagePair[]>([]);
  const [selectedPage, setSelectedPage] = useState<{ pageNumber: number; filePath: string | null } | null>(null);
  const outputRef = useRef<HTMLDivElement>(null);
  const [uploadedFilePath, setUploadedFilePath] = useState<UploadedFilePath[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('claude-3-haiku-20240307');
  const [selectedScript, setSelectedScript] = useState<'process-detailed.py' | 'process-brief.py' | 'timelines.py' | 'process-comprehensive.py'>('process-brief.py');
  const [savedResponses, setSavedResponses] = useState<SavedResponse[]>([]);
  const [displayedContent, setDisplayedContent] = useState<DisplayedContent | null>(null);
  const [displayedSavedResponse, setDisplayedSavedResponse] = useState<SavedResponse | null>(null);
  const [expandedFiles, setExpandedFiles] = useState<Record<string, boolean>>({});
  const [expandedSavedFiles, setExpandedSavedFiles] = useState<Record<string, boolean>>({});
  const [renderedOutput, setRenderedOutput] = useState<JSX.Element | null>(null);
  const [isScriptModalOpen, setIsScriptModalOpen] = useState(false);
  const logMessages = useRef<string[]>([]); // Array to store log messages
  const [filesUploaded, setFilesUploaded] = useState(false);
  const [showUploadInterface, setShowUploadInterface] = useState(true);
  const [isAboutModalOpen, setIsAboutModalOpen] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalStep, setModalStep] = useState(1);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFilePath[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [errorModalIsOpen, setErrorModalIsOpen] = useState(false);
  const [baseTemplate, setBaseTemplate] = useState<string>(`The default template is below. To replace the default template with your own, remove the text below.
---------------------------------------------------------------------------
1. Extract all important details from the current page, including but not limited to:

- Individuals mentioned, including their full names, roles, badge numbers, and specific actions

- Allegations, charges, and/or rule violations, providing case numbers and exact dates when available

- Main events, actions, and/or observations described, including precise dates and locations when provided

- Relevant evidence or findings presented

- Legal proceedings, motions, disciplinary actions, or investigation outcomes, including specific dates, case law citations, and arguments made by involved parties

- Include all relevant details from the current page, even if they do not fall under the categories of key information outlined in the guidelines.
`);


  const [summaryDescription, setSummaryDescription] = useState('');
  const [customTemplate, setCustomTemplate] = useState<string>(baseTemplate);
  const [isLoading, setIsLoading] = useState(false);

  const [sendEmail, setSendEmail] = useState(false);
  const [userEmail, setUserEmail] = useState('');
  
  const handleSummaryDescriptionChange = (description: string) => {
    setSummaryDescription(description);
    setCustomTemplate(description ? `${description}\n\n${baseTemplate.trim()}` : baseTemplate);
  };

  // const logToFile = (message: string) => {
  //   logMessages.current.push(message + '\n');
  // };

  // const saveLogToFile = () => {
  //   const blob = new Blob(logMessages.current, { type: 'text/plain;charset=utf-8' });
  //   saveAs(blob, 'log.txt');
  //   logMessages.current = []; // Clear the log messages array after saving
  // };

  const toggleExpanded = (filename: string) => {
    setExpandedFiles((prevState) => ({
      ...prevState,
      [filename]: !prevState[filename],
    }));
  };

  const toggleExpandedSaved = (filename: string) => {
    setExpandedSavedFiles((prevState) => ({
      ...prevState,
      [filename]: !prevState[filename],
    }));
  };

  
  const handlePageClick = (pageNumber: number, filename: string) => {
    const uploadedFile = uploadedFilePath.find((file: UploadedFilePath) => file.filename === filename);
    const filePath = uploadedFile?.pdfFileUrl || null;
    setSelectedPage({ pageNumber, filePath });
  };

  const convertFilesToUploadedFilePaths = (files: File[]): UploadedFilePath[] => {
    return files.map((file, index) => ({
      id: index,
      filename: file.name,
      pdfFileUrl: URL.createObjectURL(file)
    }));
  };

  const handleFileUpload = async (files: File[]) => {
    handleClearScreen();
    setSelectedFiles(files);
    setIsModalOpen(true);
    setModalStep(1);
    setFilesUploaded(true);
    setShowUploadInterface(false);
    setProcessingStatus('processing');
    // Simulate file processing
    for (let i = 0; i <= 100; i++) {
      setLoadingProgress(i);
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    setProcessingStatus('complete');
  };

  const handleScriptSelection = (scriptValue: string) => {
    setSelectedScript(scriptValue as 'process-detailed.py' | 'process-brief.py' | 'timelines.py' | 'process-comprehensive.py');
  };

  const handleShowUploadInterface = () => {
    setShowUploadInterface(prev => !prev);
  };
  

  const handleModelSelection = (modelValue: string) => {
    setSelectedModel(modelValue);
  };

  const handleNextStep = () => {
    if (modalStep < 3) {
      setModalStep(prevStep => prevStep + 1);
    }
  };

  const handlePreviousStep = () => {
    if (modalStep > 1) {
      setModalStep(prevStep => prevStep - 1);
    }
  };


  const processFiles = async () => {
    setIsLoading(true);
    setProcessingStatus('processing');
    setIsModalOpen(false);
  
    // logToFile('Starting file processing...');
  
    const formData = new FormData();
    selectedFiles.forEach(file => formData.append('files', file));
    formData.append('script', selectedScript);
    formData.append('model', selectedModel);
    formData.append('custom_template', customTemplate);
    formData.append('send_email', sendEmail.toString());
    formData.append('user_email', userEmail);
  
    // logToFile(`FormData prepared with script: ${selectedScript}, model: ${selectedModel}, send_email: ${sendEmail}, user_email: ${userEmail}`);
  
    try {
      // logToFile('Sending POST request to /api/upload...');
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
        signal: AbortSignal.timeout(9 * 60 * 1000) // 9 minutes timeout
      });
  
      if (response.ok) {
        const data = await response.json();
        // logToFile(`Response from /api/upload: ${JSON.stringify(data)}`);
        if (data.uniqueId) {
          // logToFile(`Received uniqueId: ${data.uniqueId}`);
          pollFirestore(data.uniqueId);
          setFilesUploaded(true);
  
          const uploadedFilePaths = convertFilesToUploadedFilePaths(selectedFiles);
          setUploadedFiles(uploadedFilePaths);
          // logToFile(`Uploaded file paths set: ${JSON.stringify(uploadedFilePaths)}`);
        } else {
          throw new Error('No uniqueId received from server');
        }
      } else {
        throw new Error(`Upload failed with status: ${response.status}`);
      }
    } catch (error) {
      // logToFile(`Upload error: ${error instanceof Error ? error.message : JSON.stringify(error)}`);
      console.error('Upload error:', error);
      setErrorModalIsOpen(true);
    } finally {
      setIsLoading(false);
      // logToFile('File processing completed.');
      // saveLogToFile();
    }
  };
  
  const closeErrorModal = () => {
    setErrorModalIsOpen(false);
  };
  
  const pollFirestore = async (uniqueId: string) => {
    // logToFile('Starting to poll Firestore with uniqueId: ' + uniqueId);
    const interval = setInterval(async () => {
      try {
        // logToFile('Polling Firestore...');
        const q = query(collection(db, 'uploads'), where('id', '==', uniqueId));
        const querySnapshot = await getDocs(q);
  
        if (!querySnapshot.empty) {
          // logToFile('Firestore query returned documents.');
          const uploadedFilesData: UploadedFilePath[] = [];
          const groupedSentencePagePairs: Record<string, SentencePagePair[]> = {};
  
          querySnapshot.forEach(doc => {
            const data = doc.data();
            // logToFile('Processing document: ' + JSON.stringify(data));
  
            if (data && data.pdfFileUrl && data.processedData) {
              uploadedFilesData.push({
                id: data.id,
                filename: data.filename,
                pdfFileUrl: data.pdfFileUrl
              });
  
              const processedData: ProcessedDataItem[] = JSON.parse(data.processedData);
              processedData.forEach((item: ProcessedDataItem) => {
                item.files.forEach(file => {
                  if (!groupedSentencePagePairs[file.filename]) {
                    groupedSentencePagePairs[file.filename] = [];
                  }
  
                  if (selectedScript === 'timelines.py') {
                    groupedSentencePagePairs[file.filename].push({
                      filename: file.filename,
                      sentence: file.sentence,
                      page_numbers: file.page_numbers
                    });
                  } else {
                    groupedSentencePagePairs[file.filename].push({
                      filename: file.filename,
                      sentence: file.sentence,
                      start_page: file.start_page,
                      end_page: file.end_page
                    });
                  }
                });
              });
            }
          });
  
          clearInterval(interval);
          setUploadedFiles(uploadedFilesData);
          setDisplayedContent({ groupedSentencePagePairs });
          // logToFile('Uploaded files updated: ' + JSON.stringify(uploadedFilesData));
          // logToFile('Grouped sentence-page pairs: ' + JSON.stringify(groupedSentencePagePairs));
          setDisplayedSavedResponse(null);
          setProcessingStatus('complete');
          setIsLoading(false);
          // logToFile('Processing completed and interval cleared.');
        } else {
          // logToFile('No documents found for the given uniqueId.');
        }
      } catch (error) {
        // logToFile('Error while polling Firestore: ' + (error instanceof Error ? error.message : JSON.stringify(error)));
        clearInterval(interval);
        setProcessingStatus('idle');
        setIsLoading(false);
        // saveLogToFile();
      }
    }, 20000);
  };
  
  
  useEffect(() => {
    if (displayedContent) {
      // logToFile('Displayed content: ' + JSON.stringify(displayedContent));
      // logToFile('Uploaded files: ' + JSON.stringify(uploadedFiles));
  
      const output = (
        <div className={styles.displayedContentArea}>
          {Object.entries(displayedContent.groupedSentencePagePairs).map(([filename, sentencePagePairs]) => {
            // logToFile('Processing filename: ' + filename);
            // logToFile('Sentence-page pairs: ' + JSON.stringify(sentencePagePairs));
  
            // Clean the filename
            const cleanedFilename = filename.replace(/^\S+?_/, '').replace('.json', '');
            // logToFile('Cleaned filename: ' + cleanedFilename);
  
            return (
              <div key={filename}>
                <button
                  className={styles.collapsibleButton}
                  onClick={() => {
                    toggleExpanded(filename);
                    const savedContentStr = localStorage.getItem('displayedContent');
                    if (savedContentStr) {
                      const savedContent = JSON.parse(savedContentStr);
                      if (savedContent && savedContent.filename === filename) {
                        setDisplayedContent(savedContent);
                      }
                    }
                  }}
                >
                  {cleanedFilename}
                </button>
                {expandedFiles[filename] && (
                  <div className={styles.collapsibleContent}>
                    {sentencePagePairs.map((pair, index) => {
                      const trimmedFilename = filename.split('_')[1].split('.')[0].trim();
                      const matchedFile = uploadedFiles.find((file) =>
                        file.filename.includes(trimmedFilename)
                      );
  
                      // logToFile('Trimmed filename: ' + trimmedFilename);
                      // logToFile('Matched file: ' + JSON.stringify(matchedFile));
  
                      const pdfFileUrl = matchedFile?.pdfFileUrl;
                      // logToFile('PDF File URL: ' + pdfFileUrl);
  
                      // Check if selectedScript is 'timelines.py'
                      if (selectedScript === 'timelines.py' && pair.page_numbers) {
                        return (
                          <div key={index}>
                            <div className={styles.pageRange}>
                              Pages {pair.page_numbers.join(', ')}
                            </div>
                            <div style={{ display: 'block', marginBottom: '10px' }}>
                              <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>{pair.sentence}</pre>
                            </div>
                            {pair.page_numbers.map((pageNumber) => (
                              <div key={pageNumber}>
                                <a
                                  href={`${pdfFileUrl}#page=${pageNumber}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className={styles.pdfLinkButton}
                                >
                                  View PDF File (Page {pageNumber})
                                </a>
                              </div>
                            ))}
                          </div>
                        );
                      } else if (pair.start_page !== undefined && pair.end_page !== undefined) {
                        return (
                          <div key={index}>
                            <div className={styles.pageRange}>
                              Pages {pair.start_page} - {pair.end_page}
                            </div>
                            <div style={{ display: 'block', marginBottom: '10px' }}>
                              <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>{pair.sentence}</pre>
                            </div>
                            <div>
                              <a
                                href={`${pdfFileUrl}#page=${pair.start_page}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className={styles.pdfLinkButton}
                              >
                                View PDF File (Page {pair.start_page})
                              </a>
                            </div>
                          </div>
                        );
                      } else {
                        return null;
                      }
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      );
  
      // logToFile('Rendered output: ' + JSON.stringify(output));
      // saveLogToFile();
      setRenderedOutput(output);
      localStorage.setItem('displayedContent', JSON.stringify(displayedContent));
    }
  }, [displayedContent, selectedScript, expandedFiles, uploadedFiles]);
  

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [sentencePagePairs]);

  const handleClearScreen = () => {
    // logToFile('Clearing screen');
    setFiles([]);
    setSelectedFiles([]);
    setSummaryDescription('');
    setDisplayedContent(null);
    setLoadingProgress(0);
    setDisplayedSavedResponse(null);
    setProcessingStatus('idle');
    setRenderedOutput(null);
    setUploadedFiles([]); // Clear the uploadedFiles state
    setFilesUploaded(false); // Reset filesUploaded state
    // saveLogToFile(); // Save log file when clearing the screen
  };

  useEffect(() => {
    const saved = localStorage.getItem('savedResponses');
    if (process.env.NODE_ENV === 'development') {
      localStorage.clear();
    } else if (saved) {
      setSavedResponses(JSON.parse(saved) as SavedResponse[]);
    }
  }, []);

  const saveResponseToLocalStorage = (content: DisplayedContent) => {
    const newResponseId = savedResponses.length + 1;
    const pdfUrls = uploadedFiles.map(file => ({
      id: file.id,
      filename: file.filename,
      pdfFileUrl: file.pdfFileUrl
    }));
    const newResponse: SavedResponse = {
      id: newResponseId,
      label: `Saved Response ${newResponseId}`,
      script: selectedScript, // Ensure selectedScript has the correct type
      content: displayedContent,
      pdfUrls: pdfUrls,
      renderedOutput: '' // or some initial value
    };
    const updatedResponses = [...savedResponses, newResponse];
    setSavedResponses(updatedResponses);
    localStorage.setItem('savedResponses', JSON.stringify(updatedResponses));
  };

  const handleDisplaySavedResponse = (response: SavedResponse) => {
    setDisplayedSavedResponse(response);
    setDisplayedContent(response.content);
    if (response.pdfUrls) {
      const updatedFiles = response.pdfUrls.map(url => ({ id: url.id, filename: url.filename, pdfFileUrl: url.pdfFileUrl }));
      setUploadedFiles(updatedFiles);
    }
  };
  

  const handleRenameSavedResponse = (responseId: number, newLabel: string) => {
    const updatedResponses = savedResponses.map((response) => {
      if (response.id === responseId) {
        return { ...response, label: newLabel };
      }
      return response;
    });
    setSavedResponses(updatedResponses);
    localStorage.setItem('savedResponses', JSON.stringify(updatedResponses));
  };

  const handleDeleteSavedResponse = (responseId: number) => {
    const updatedResponses = savedResponses.filter((response) => response.id !== responseId);
    setSavedResponses(updatedResponses);
    localStorage.setItem('savedResponses', JSON.stringify(updatedResponses));
  };

  const handleFilesSelected = () => {
    setFilesUploaded(true);
  };

  const openAboutModal = () => {
    setIsAboutModalOpen(true);
  };

  const closeAboutModal = () => {
    setIsAboutModalOpen(false);
  };

  const scriptOptions = [
    { value: 'process-comprehensive.py', label: 'Comprehensive Summary', description: 'Generate a summary for every page of your document.'  },
    { value: 'process-brief.py', label: 'Brief Summary', description: 'Generate a comprehensive summary for the entire document.'},
    { value: 'process-detailed.py', label: 'Detailed Summary',  description: 'Generate one comprehensive summary for every 12 pages of your document.' },
    // { value: 'timelines.py', label: 'Generate a Timeline of Events' },
  ];
  
  const modelOptions = [
    { value: 'claude-3-haiku-20240307', label: 'Claude-3 Haiku' },
  ];
  

  return (
    <div className={styles.container}>
      <div className={styles.contentContainer}>
        <Sidebar
          onPageClick={handlePageClick}
          sentencePagePairs={sentencePagePairs}
          onSavedResponseClick={handleDisplaySavedResponse}
          savedResponses={savedResponses}
          onDeleteSavedResponse={handleDeleteSavedResponse}
          onRenameSavedResponse={handleRenameSavedResponse}
          onSaveOutput={saveResponseToLocalStorage}
          lastUploadedData={displayedContent}
        />
        <div className={styles.outputContainer}>
          <div className={styles.headerSection}>
            <Image src="/logo-grey-v4.png" alt="Logo" width={200} height={100} />
            <button onClick={openAboutModal} className={styles.aboutButton}>
              About
            </button>
            <button onClick={handleShowUploadInterface} className={styles.showUploadButton}>
              <Plus size={24} />
            </button>
          </div>
          <hr className={styles.headerDivider} />

            {/* Script options section with conditional rendering */}
          {(!filesUploaded && showUploadInterface) && (
            <div className={styles.scriptOptionsContainer}>
              <div className={styles.scriptOptionsRow}>
                {scriptOptions.map((option) => (
                  <div key={option.value} className={styles.scriptOptionCard}>
                    <h3 className={styles.scriptOptionTitle}>{option.label}</h3>
                    <p className={styles.scriptOptionDescription}>{option.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}


          <LoadingBar isLoading={isLoading} />
          {renderedOutput}
  
          {displayedSavedResponse && displayedSavedResponse.renderedOutput && (
            <div
              className={styles.displayedSavedResponseArea}
              dangerouslySetInnerHTML={{ __html: displayedSavedResponse.renderedOutput }}
            />
          )}
              
          {(!filesUploaded || showUploadInterface) && (
            <div className={styles.uploadInputContainer}>
              <input
                type="text"
                placeholder="Describe some essential details to include in your summary"
                value={summaryDescription}
                onChange={(e) => handleSummaryDescriptionChange(e.target.value)}
                className={styles.summaryInput}
              />
              <input
                type="file"
                accept=".pdf, .jpeg, .jpg, .png"
                onChange={(e) => {
                  if (e.target.files) {
                    handleFileUpload(Array.from(e.target.files));
                  }
                }}
                className={styles.fileInput}
                id="fileInput"
                multiple
                disabled={processingStatus === 'processing'}
              />
              <label htmlFor="fileInput" className={styles.fileInputLabel} aria-label="Select files">
                <ArrowUp size={24} />
              </label>
            </div>
          )}
        </div>
      </div>
  
      {/* Processing Options Modal */}
      <Modal
        isOpen={isModalOpen}
        onRequestClose={() => setIsModalOpen(false)}
        contentLabel="Processing Options Modal"
        className={styles.processingModal}
        overlayClassName={styles.processingModalOverlay}
      >
        <div className={styles.modalContent}>
          <button onClick={() => setIsModalOpen(false)} className={styles.processingModalCloseButton}>
            <X size={24} />
          </button>
          <h2 className={styles.modalTitle}>
            {modalStep === 1 ? "Select a Summary Type" : 
            modalStep === 2 ? "Customize Your Summary" : 
            "Email Preferences"}
          </h2>
          {modalStep === 1 && (
            <div className={styles.modalStep}>
              <div className={styles.optionsGrid}>
                {scriptOptions.map((option) => (
                  <div
                    key={option.value}
                    className={`${styles.optionCard} ${selectedScript === option.value ? styles.selectedCard : ''}`}
                    onClick={() => handleScriptSelection(option.value)}
                  >
                    <h3 className={styles.optionTitle}>{option.label}</h3>
                    <p className={styles.optionDescription}>{option.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
          {modalStep === 2 && (
            <div className={styles.modalStep}>
              <textarea
                value={customTemplate}
                onChange={(e) => setCustomTemplate(e.target.value)}
                className={styles.customTemplateTextArea}
                rows={10}
              />
            </div>
          )}
          {modalStep === 3 && (
            <div className={styles.modalStep}>
              <EmailCard
                sendEmail={sendEmail}
                setSendEmail={setSendEmail}
                userEmail={userEmail}
                setUserEmail={setUserEmail}
              />
            </div>
          )}
          <div className={styles.modalButtons}>
            {modalStep > 1 && (
              <button onClick={handlePreviousStep} className={styles.previousButton}>
                <ArrowLeft size={16} /> Back
              </button>
            )}
            {modalStep < 3 ? (
              <button 
                onClick={handleNextStep} 
                className={styles.nextButton} 
                disabled={modalStep === 1 && !selectedScript}
              >
                Next <ArrowRight size={16} />
              </button>
            ) : (
              <button 
                onClick={processFiles} 
                className={styles.processButton} 
                disabled={!customTemplate.trim() || (sendEmail && !userEmail.trim())}
              >
                Process <ArrowRight size={16} />
              </button>
            )}
          </div>
        </div>
      </Modal>
  
      {/* Error Modal */}
      <Modal
        isOpen={errorModalIsOpen}
        onRequestClose={closeErrorModal}
        contentLabel="Error Modal"
        className={styles.modal}
        overlayClassName={styles.modalOverlay}
      >
        <div className={styles.modalContent}>
          <button onClick={closeErrorModal} className={styles.errorModalButton}>
            <X size={50} />
          </button>
          <h2 className={styles.modalTitle}>Upload Error: The file exceeds the limit or is corrupted. Please try again with a different file.</h2>
        </div>
      </Modal>
  
      {/* About Modal */}
      <Modal
        isOpen={isAboutModalOpen}
        onRequestClose={closeAboutModal}
        contentLabel="About Modal"
        className={styles.modal}
        overlayClassName={styles.modalOverlay}
      >
        <AboutContent />
        <button onClick={closeAboutModal} className={styles.modalCloseButton}>
          Close
        </button>
      </Modal>
    </div>
  );
};

export default UploadInterface;
