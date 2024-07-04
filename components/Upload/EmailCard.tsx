import React, { useState } from 'react';
import { Mail, Info, CheckCircle, AlertCircle } from 'lucide-react';
import styles from './EmailCard.module.scss';

interface EmailCardProps {
  sendEmail: boolean;
  setSendEmail: (send: boolean) => void;
  userEmail: string;
  setUserEmail: (email: string) => void;
}

const EmailCard: React.FC<EmailCardProps> = ({ sendEmail, setSendEmail, userEmail, setUserEmail }) => {
  const [isEmailValid, setIsEmailValid] = useState(true);

  const validateEmail = (email: string) => {
    const re = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return re.test(String(email).toLowerCase());
  };

  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const email = e.target.value;
    setUserEmail(email);
    setIsEmailValid(validateEmail(email));
  };

  return (
    <div className={styles.emailCard}>
      <div className={styles.cardHeader}>
        <h3 className={styles.cardTitle}>Notification Preferences</h3>
        <Info className={styles.infoIcon} size={18} />
      </div>
      <p className={styles.processingInfo}>Summaries can take up to 10 minutes to process.</p>
      <p className={styles.optionIntro}>Would you like to receive an email notification when your summary is ready?</p>
      <div className={styles.optionsContainer}>
        <label className={`${styles.option} ${sendEmail ? styles.selectedOption : ''}`}>
          <input
            type="radio"
            name="emailPreference"
            checked={sendEmail}
            onChange={() => setSendEmail(true)}
          />
          <span>Yes, notify me</span>
        </label>
        <label className={`${styles.option} ${!sendEmail ? styles.selectedOption : ''}`}>
          <input
            type="radio"
            name="emailPreference"
            checked={!sendEmail}
            onChange={() => setSendEmail(false)}
          />
          <span>No, thanks</span>
        </label>
      </div>
      {sendEmail && (
        <div className={`${styles.emailInputContainer} ${isEmailValid ? styles.validEmail : styles.invalidEmail}`}>
          <Mail className={styles.emailIcon} size={18} />
          <input
            type="email"
            value={userEmail}
            onChange={handleEmailChange}
            placeholder="Enter your email address"
            className={styles.emailInput}
          />
          {userEmail && (
            isEmailValid 
              ? <CheckCircle className={styles.validationIcon} size={18} /> 
              : <AlertCircle className={styles.validationIcon} size={18} />
          )}
        </div>
      )}
    </div>
  );
};

export default EmailCard;