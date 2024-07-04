import React, { useState } from 'react';
import styles from './AboutContent.module.scss';

const AboutContent: React.FC = () => {
  const [activeTab, setActiveTab] = useState('about');

  return (
    <div className={styles.container}>
      <div className={styles.tabContainer}>
        <button className={`${styles.tab} ${activeTab === 'about' ? styles.active : ''}`} onClick={() => setActiveTab('about')}>About</button>
        <button className={`${styles.tab} ${activeTab === 'howToUse' ? styles.active : ''}`} onClick={() => setActiveTab('howToUse')}>How to Use</button>
        <button className={`${styles.tab} ${activeTab === 'comingSoon' ? styles.active : ''}`} onClick={() => setActiveTab('comingSoon')}>Coming Soon</button>
        <button className={`${styles.tab} ${activeTab === 'security' ? styles.active : ''}`} onClick={() => setActiveTab('security')}>Security</button>
      </div>

      <div className={styles.tabContent}>
        {activeTab === 'about' && (
          <div>
            <h2 className={styles.title}>About ML Justice Lab</h2>
            <p className={styles.description}>
              ML Justice Lab is a project dedicated to leveraging machine learning techniques to enhance justice and legal systems. Our goal is to provide tools and insights that can assist in the analysis and understanding of legal documents and data.
            </p>
            <p className={styles.description}>
              Our application allows users to upload legal documents in PDF format and process them using advanced natural language processing algorithms. The processed data is then presented in a structured and searchable format, making it easier for legal professionals to extract relevant information and insights.
            </p>
          </div>
        )}

        {activeTab === 'howToUse' && (
          <div>
            <h3 className={styles.subtitle}>How to Use</h3>
            <p className={styles.description}>
              Our application offers three modes for processing and summarizing legal documents:
            </p>
            <ol className={styles.modeList}>
              <li>Generate Brief Summary: Generates a single summary for the entire document.</li>
              <li>Generate Detailed Summary: Generates a summary for every 12 pages of the document.</li>
              <li>Generate Comprehensive Summary: Generates a summary for each page of the document.</li>
              <li>All PDFs must be under 5mb.</li>
            </ol>


            <h4 className={styles.subtitle}>Selecting a Model</h4>
            <p className={styles.description}>
              You can choose between two large language models for processing your documents:
            </p>
            <ul className={styles.modelList}>
              <li>Claude-3 Haiku (Anthropic)</li>
              <li>Other models are available on request</li>
            </ul>

            <h4 className={styles.subtitle}>General Instructions</h4>
            <p className={styles.description}>
              1. Upload Files: Click the &quot;Upload Files&quot; button to select and upload your documents.
            </p>
            <p className={styles.description}>
              2. Select Summary Type: Use the dropdown menu in the top left corner to choose the type of summary you want to generate (Brief, Detailed, Comprehensive).
            </p>
            <p className={styles.description}>
              3. Choose Model: Use the dropdown menu in the top left corner to select the language model (Claude-3 Haiku or GPT-3.5-Turbo).
            </p>
            <p className={styles.description}>
              4. Custom Mode (Optional): Click the &quot;Custom Mode&quot; button in the top right corner to edit the main template used to generate summaries. 
            </p>

            <h4 className={styles.subtitle}>Custom Mode</h4>
            <p className={styles.description}>
              Custom Mode allows you to tailor the summary template to better fit your specific needs. You can adjust parameters and settings to refine the output. Note that this feature is optional and is designed for users who have experience with prompt engineering.
            </p>

            <p className={styles.description}>
              For more information on prompt engineering and best practices, visit <a href="https://help.openai.com/en/articles/6654000-best-practices-for-prompt-engineering-with-the-openai-api" target="_blank" rel="noopener noreferrer" style={{color: 'blue'}}>this link</a>.
            </p>
          </div>
        )}

        {activeTab === 'comingSoon' && (
          <div>
            <h3 className={styles.subtitle}>Coming Soon</h3>
            <p className={styles.description}>
              We are constantly working to improve our application and add new features. Here are some exciting updates that will be available soon:
            </p>
            <ul className={styles.bulletPoints}>
              <li>Generate a timeline of events mentioned in the document.</li>
              <li>Extract entities such as places, persons, and things from the document.</li>
              <li>Integration of open source models that can be used on private servers for sensitive data.</li>
            </ul>
          </div>
        )}

        {activeTab === 'security' && (
          <div>
            <h3 className={styles.subtitle}>Model Security and Privacy</h3>
            <h4 className={styles.modelTitle}>Anthropic</h4>
            <p className={styles.description}>
              According to Anthropic&apos;s data usage policy, they will not use your inputs or outputs to train their models, unless:
            </p>
            <ul className={styles.bulletPoints}>
              <li>Your conversations are flagged for Trust & Safety review, in which case they may use or analyze them to improve their ability to detect and enforce their Usage Policy, including training models for use by their Trust and Safety team, consistent with Anthropic&apos;s safety mission.</li>
              <li>You&apos;ve explicitly reported the materials to them, for example, via their feedback mechanisms.</li>
              <li>You&apos;ve otherwise explicitly opted in to training.</li>
            </ul>
            <p className={styles.description}>
              Anthropic&apos;s compliance and certifications include:
            </p>
            <ul className={styles.bulletPoints}>
              <li>SOC 2 Type I: Audit confirming the design of security processes and controls.</li>
              <li>SOC 2 Type II: Audit confirming the operational effectiveness of security processes and controls over time.</li>
              <li>HIPAA: Compliance with the Health Insurance Portability and Accountability Act, ensuring the protection of health information.</li>
            </ul>
            <p className={styles.description}>
              For more information about how Anthropic uses personal data in model training, please visit their <a href="https://support.anthropic.com/en/articles/7996885-how-do-you-use-personal-data-in-model-training" target="_blank" rel="noopener noreferrer" style={{color: 'blue'}}>support article</a>.
            </p>

            <h3 className={styles.subtitle}>Storage Security and Privacy</h3>
            <p className={styles.description}>
              We leverage Firebase, a Google Cloud platform, to store and manage user data securely. Firebase employs industry-standard security measures and complies with major privacy regulations to ensure the protection of your data.
            </p>

            <h4 className={styles.sectionTitle}>Data Encryption</h4>
            <p className={styles.description}>
              Firebase uses advanced encryption techniques to safeguard your data:
            </p>
            <ul className={styles.bulletPoints}>
              <li>All data transmitted between the client and Firebase is encrypted using HTTPS/SSL, ensuring secure communication.</li>
              <li>Data stored in Firebase is encrypted at rest using AES-256 encryption, providing a high level of protection.</li>
              <li>Firebase follows secure key management practices to maintain the confidentiality and integrity of encryption keys.</li>
            </ul>

            <h4 className={styles.sectionTitle}>Certifications and Standards</h4>
            <p className={styles.description}>
              Firebase services have successfully completed rigorous security and privacy evaluations:
            </p>
            <ul className={styles.bulletPoints}>
              <li>ISO 27001, ISO 27017, and ISO 27018 certification, demonstrating Firebase&apos;s commitment to information security and privacy.</li>
              <li>SOC 1, SOC 2, and SOC 3 compliance, verifying the effectiveness of Firebase&apos;s security controls.</li>
              <li>Compliance reports and certificates are available upon request for Firebase services governed by the GCP Terms of Service.</li>
            </ul>
            <p className={styles.description}>
              For more information about Firebase&apos;s privacy and security practices, please visit the <a href="https://firebase.google.com/support/privacy" target="_blank" rel="noopener noreferrer" style={{color: 'blue'}}>Firebase Privacy and Security</a> page.
            </p>

            <h4 className={styles.sectionTitle}>Data Retention</h4>
            <p className={styles.description}>
              We understand the importance of data privacy and minimizing data retention. By default, all user data processed by our application is automatically deleted on a daily basis. However, if you choose to save your data, it will be securely stored until you explicitly delete it or request its removal.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AboutContent;
