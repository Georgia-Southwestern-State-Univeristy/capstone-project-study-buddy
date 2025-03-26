import { Component, OnInit } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  FormControl,
  FormArray,
  Validators
} from '@angular/forms';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import Docxtemplater from 'docxtemplater';
import PizZip from 'pizzip';
import PizZipUtils from 'pizzip/utils/index.js';
import { saveAs } from 'file-saver';
import { AppService } from 'src/app/app.service';
function loadFile(
  url: string,
  callback: (error: Error | null, content: string) => void
) {
  PizZipUtils.getBinaryContent(url, callback);
}

@Component({
  selector: 'app-resume-builder',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './resume-builder.component.html',
  styleUrls: ['./resume-builder.component.scss']
})
export class ResumeBuilderComponent implements OnInit {
  personForm!: FormGroup;

  createdResumeId: string | null = null;   // store the newly created resume ID
  enhancedResumeText: string | null = null; // store AI-improved text
  atsScore: number | null = null;           // store ATS score from AI
  isImproving = false;                      // UI flag to show "Enhancing..."
  activeTab = 'personal';
  currentStep = 1; // For progress indicator
  availableTabs = ['personal', 'education', 'experience', 'skills', 'projects'];
  formProgress = {
    personal: 0,
    education: 0,
    experience: 0,
    skills: 0,
    projects: 0
  };
  
  // Translation related properties
  preferredLanguage: string = 'en';
  translatedTexts: { [key: string]: string } = {};


  showSuccessDialog = false;
successDialogTitle = '';
successDialogMessage = '';
showResumeIdInDialog = false;
showAtsScoreInDialog = false;

showErrorDialog = false;
errorDialogTitle = '';
errorDialogMessage = '';
errorDetails = '';
errorRetryAction: (() => void) | null = null;

showInfoDialog = false;
infoDialogTitle = '';
infoDialogMessage = '';
infoDialogConfirmText = 'Confirm';
infoDialogConfirmIcon = 'fa-check';
infoDialogAction: (() => void) | null = null;

  constructor(
    private fb: FormBuilder,
    private appService: AppService
  ) {}

  ngOnInit(): void {
    this.personForm = this.fb.group({
      // Basic personal info
      fName: [''],
      lName: [''],
      description: [''],

      // Career
      career: [''],
      career2: [''],
      career3: [''],

      // Contact
      phoneNum: [''],
      email: [''],
      website: [''],

      // Instead of a single "socialmedia" field,
      // we store multiple social accounts in a FormArray:
      socialAccounts: this.fb.array([]),

      // Skills / Achievements
      skills: [''],
      achievements: [''],
      certifications: [''],

      // Dynamic sections (FormArrays)
      education: this.fb.array([this.createEducationItem()]),
      experience: this.fb.array([this.createExperienceItem()]),
      projects: this.fb.array([]), // Start empty or add initial item if desired
      references: this.fb.array([])
    });
    
    // Get user's preferred language
    this.preferredLanguage = localStorage.getItem('preferredLanguage') || 'en';
    
    // Only translate if language is not English
    if (this.preferredLanguage !== 'en') {
      this.translateContent(this.preferredLanguage);
    }
  }

  // Translation method to translate static content
  private translateContent(targetLanguage: string) {
    const elementsToTranslate = document.querySelectorAll('[data-translate]');
    const textsToTranslate = Array.from(elementsToTranslate).map(
      (el) => el.textContent?.trim() || ''
    );

    // Include additional texts that need translation
    const additionalTexts = [
      // Resume Builder
      'Resume Builder',
      'Create a professional resume in minutes with AI enhancement',
      
      // Tabs
      'Personal', 'Education', 'Experience', 'Skills', 'Projects',
      
      // Personal Info
      'Personal Information', 'First Name', 'Last Name', 'Professional Summary',
      'Your legal first name', 'Briefly describe your professional background and career goals',
      
      // Career Goals
      'Career Goals', 'Primary Career Goal', 'Alternate Career',
      'e.g. Software Engineer', 'e.g. Data Scientist', 'e.g. Web Developer',
      
      // Contact Info
      'Contact Information', 'Mobile Number', 'E-mail', 'Personal Website',
      'Social Media Accounts', 'Add your professional social media profiles',
      'Platform', 'Handle', 'Profile URL', 'Add Social Media Profile',
      'Select platform', 'LinkedIn', 'GitHub', 'Twitter', 'Instagram', 'Other',
      'e.g. @john_doe', 'e.g. https://www.linkedin.com/in/john-doe',
      
      // Education
      'School/University Name', 'Graduation Date', 'Degree/Major', 'Add Education',
      'e.g. Georgia Southwestern University', 'e.g. B.S. in Computer Science',
      
      // Experience
      'Work Experience', 'Company Name', 'Employment Period', 'Description of Role',
      'e.g. Google', 'e.g. 2021 - 2023', 'Add Work Experience',
      'Describe your responsibilities, achievements, and technologies used',
      'Pro tip: Use action verbs and quantify your achievements when possible',
      
      // Skills
      'Skills & Achievements', 'Technical Skills',
      'List your relevant skills (e.g. Java, React, Project Management)',
      'Achievements/Awards', 'e.g. Dean\'s List, Hackathon Winner, etc.',
      'Certifications', 'e.g. AWS Certified, PMP, etc.', 'JavaScript','Python','React','Angular','Node.js',
      
      // Projects
      'Project Name', 'Project URL', 'Project Description','Add Project',
      'e.g. Personal Portfolio',
      'e.g. https://github.com/yourusername/project',
      'Describe the project, your role, technologies used, and outcomes',
      
      // References
      'References', 'Reference Name', 'Contact Info','Add Reference',
      'e.g. John Doe', 'Email or Phone',
      
      // Buttons
      'Previous', 'Next', 'Save Resume', 'Download Draft',
      'Enhance with AI', 'Enhancing Resume...', 'Download Enhanced',
      
      // Progress steps
      'Create Resume', 'Save', 'Enhance', 'Download',
      
      // Enhancement section
      'Resume ID:', 'AI-Enhanced Resume', 'ATS Score',
      
      // Tips
      'Keywords optimized for increased visibility by recruiters\' automated systems.',
      'Professional tone and language improved for better industry alignment.',
      'Grammar and formatting perfected for professional appearance.',
      
      // Dialog texts
      'Continue', 'Close', 'Try Again', 'Cancel', 'Confirm',
      'Your resume has been saved successfully with ID:',

      // Add more as needed
      'Resume Created Successfully',
      'Your resume has been saved to our database and is ready for enhancement.',
      'Resume Enhancement Failed',
      'An error occurred while enhancing your resume. Please try again.',
      'Resume Enhanced',
      'Your resume has been improved with AI technology.',
    ];
    
    const allTextsToTranslate = [...textsToTranslate, ...additionalTexts];

    // Call translation service
    this.appService
      .translateTexts(allTextsToTranslate, targetLanguage)
      .subscribe({
        next: (response) => {
          const translations = response.translations;

          // Translate texts from data-translate elements
          elementsToTranslate.forEach((element, index) => {
            const originalText = textsToTranslate[index];
            this.translatedTexts[originalText] = translations[index];

            // Update directly if it's a regular DOM element
            if (!(element.tagName.startsWith('MAT-'))) {
              element.textContent = translations[index];
            }
          });

          // Handle additional texts
          additionalTexts.forEach((text, index) => {
            const translatedText = translations[textsToTranslate.length + index];
            this.translatedTexts[text] = translatedText;
          });
          
          // After translations are loaded, update dynamic content if needed
          setTimeout(() => this.translateDynamicContent(), 100);
        },
        error: (error) => {
          console.error('Error translating texts:', error);
        }
      });
  }
  
  // Translate dynamic content (content that might be added after initial load)
  translateDynamicContent(): void {
    if (this.preferredLanguage === 'en') return;
    
    // Find all data-translate elements that might have been dynamically added
    const elementsToTranslate = document.querySelectorAll('[data-translate]');
    const textsToTranslate = Array.from(elementsToTranslate).map(
      (el) => el.textContent?.trim() || ''
    );
    
    // Filter out texts that are already translated
    const untranslatedTexts = textsToTranslate.filter(
      text => !this.translatedTexts[text] && text !== ''
    );
    
    if (untranslatedTexts.length === 0) return;
    
    this.appService.translateTexts(untranslatedTexts, this.preferredLanguage)
      .subscribe({
        next: (response) => {
          const translations = response.translations;
          
          untranslatedTexts.forEach((text, idx) => {
            this.translatedTexts[text] = translations[idx];
          });
          
          // Update the DOM elements
          elementsToTranslate.forEach(element => {
            const text = element.textContent?.trim() || '';
            if (this.translatedTexts[text] && !(element.tagName.startsWith('MAT-'))) {
              element.textContent = this.translatedTexts[text];
            }
          });
        },
        error: (err) => console.error('Error translating dynamic content:', err)
      });
  }

  // Dialog methods
showSuccess(title: string, message: string, showResumeId = false, showAtsScore = false) {
  this.successDialogTitle = title;
  this.successDialogMessage = message;
  this.showResumeIdInDialog = showResumeId;
  this.showAtsScoreInDialog = showAtsScore;
  this.showSuccessDialog = true;
}

showError(title: string, message: string, details = '', retryAction: (() => void) | null = null) {
  this.errorDialogTitle = title;
  this.errorDialogMessage = message;
  this.errorDetails = details;
  this.errorRetryAction = retryAction;
  this.showErrorDialog = true;
}

showInfo(title: string, message: string, confirmText = 'Confirm', confirmIcon = 'fa-check', action: (() => void) | null = null) {
  this.infoDialogTitle = title;
  this.infoDialogMessage = message;
  this.infoDialogConfirmText = confirmText;
  this.infoDialogConfirmIcon = confirmIcon;
  this.infoDialogAction = action;
  this.showInfoDialog = true;
}

closeDialog() {
  this.showSuccessDialog = false;
  this.showErrorDialog = false;
  this.showInfoDialog = false;
}

confirmInfoAction() {
  if (this.infoDialogAction) {
    this.infoDialogAction();
  }
  this.closeDialog();
}

retryErrorAction() {
  if (this.errorRetryAction) {
    this.errorRetryAction();
  }
  this.closeDialog();
}

  // --- Factory methods to create FormGroups for dynamic sections ---
  createEducationItem(): FormGroup {
    return this.fb.group({
      school: [''],
      grad: [''],
      major: ['']
    });
  }

  createExperienceItem(): FormGroup {
    return this.fb.group({
      exp_company: [''],
      exp_date: [''],
      exp_description: ['']
    });
  }

  createProjectItem(): FormGroup {
    return this.fb.group({
      projectName: [''],
      projectUrl: [''],
      projectDesc: ['']
    });
  }

  createReferenceItem(): FormGroup {
    return this.fb.group({
      refName: [''],
      refContact: ['']
    });
  }

  // Social accounts => each item has platform, handle, url
  createSocialAccount(): FormGroup {
    return this.fb.group({
      platform: [''],   // e.g. "LinkedIn"
      handle: [''],     // e.g. "@john_doe"
      link: ['']        // e.g. "https://www.linkedin.com/in/john-doe"
    });
  }

  // --- Getters for convenience in the template ---
  get educationControls() {
    return (this.personForm.get('education') as FormArray).controls;
  }
  get experienceControls() {
    return (this.personForm.get('experience') as FormArray).controls;
  }
  get projectControls() {
    return (this.personForm.get('projects') as FormArray).controls;
  }
  get referenceControls() {
    return (this.personForm.get('references') as FormArray).controls;
  }
  get socialAccountsControls() {
    return (this.personForm.get('socialAccounts') as FormArray).controls;
  }

  // --- Methods to add/remove items from each FormArray ---
  addEducation() {
    (this.personForm.get('education') as FormArray).push(
      this.createEducationItem()
    );
  }
  removeEducation(index: number) {
    (this.personForm.get('education') as FormArray).removeAt(index);
  }

  addExperience() {
    (this.personForm.get('experience') as FormArray).push(
      this.createExperienceItem()
    );
  }
  removeExperience(index: number) {
    (this.personForm.get('experience') as FormArray).removeAt(index);
  }

  addProject() {
    (this.personForm.get('projects') as FormArray).push(this.createProjectItem());
  }
  removeProject(index: number) {
    (this.personForm.get('projects') as FormArray).removeAt(index);
  }

  addReference() {
    (this.personForm.get('references') as FormArray).push(
      this.createReferenceItem()
    );
  }
  removeReference(index: number) {
    (this.personForm.get('references') as FormArray).removeAt(index);
  }

  addSocialAccount() {
    (this.personForm.get('socialAccounts') as FormArray).push(
      this.createSocialAccount()
    );
  }
  removeSocialAccount(index: number) {
    (this.personForm.get('socialAccounts') as FormArray).removeAt(index);
  }
  // Tab navigation methods
  setActiveTab(tab: string) {
    this.activeTab = tab;
  }
  
  goToNextTab() {
    const currentIndex = this.availableTabs.indexOf(this.activeTab);
    if (currentIndex < this.availableTabs.length - 1) {
      this.activeTab = this.availableTabs[currentIndex + 1];
    }
  }
  
  goToPreviousTab() {
    const currentIndex = this.availableTabs.indexOf(this.activeTab);
    if (currentIndex > 0) {
      this.activeTab = this.availableTabs[currentIndex - 1];
    }
  }
  
  isNextTabDisabled(): boolean {
    return this.availableTabs.indexOf(this.activeTab) === this.availableTabs.length - 1;
  }
  
  isPreviousTabDisabled(): boolean {
    return this.availableTabs.indexOf(this.activeTab) === 0;
  }
  
  // Helper for character count
  getCharacterCount(controlName: string): number {
    const control = this.personForm.get(controlName);
    return control && control.value ? control.value.length : 0;
  }
  
  // Helper for skills suggestions
  addSkill(skill: string) {
    const currentSkills = this.personForm.get('skills')?.value || '';
    if (!currentSkills.includes(skill)) {
      const updatedSkills = currentSkills ? `${currentSkills}, ${skill}` : skill;
      this.personForm.get('skills')?.setValue(updatedSkills);
    }
  }

  // *** (1) Submit => Save Resume to DB
  onSubmit() {
    const formData = this.personForm.value;

    // If your backend expects user_id from the front end, supply it (or use JWT on server side).
    formData.user_id = localStorage.getItem('user_id') || '12345';

    // Define message strings
    const successTitle = 'Resume Created Successfully';
    const successMessage = 'Your resume has been saved to our database and is ready for enhancement.';
    const errorTitle = 'Resume Creation Failed';
    const errorMessage = 'We encountered a problem while saving your resume.';

    this.appService.createResume(formData).subscribe({
      next: (res) => {
        console.log('Resume created:', res);
        this.createdResumeId = res.resume_id;
        
        // Use translated strings if available, otherwise use default English
        this.showSuccess(
          this.translatedTexts[successTitle] || successTitle,
          this.translatedTexts[successMessage] || successMessage,
          true,
          false
        );
        this.enhancedResumeText = null; // reset if we had an old AI result
        this.atsScore = null;
        this.currentStep = 2;
      },
      error: (err) => {
        console.error('Error creating resume:', err);
        
        this.showError(
          this.translatedTexts[errorTitle] || errorTitle,
          this.translatedTexts[errorMessage] || errorMessage,
          err.message || 'Unknown error',
          () => this.onSubmit() // Retry action
        );
      }
    });
  }

  // *** (2) Download Original => docxtemplater logic with user form
  downloadOriginalDocx() {
    // If the user hasn't even created or filled the form, we can still let them download the local doc...
    // If you want to only allow doc download after saving to DB, check if this.createdResumeId

    loadFile(
      '../assets/doc-templates/Resume.docx',
      (error, content) => {
        if (error) {
          console.error('Error loading template file:', error);
          return;
        }
        try {
          const zip = new PizZip(content);
          const doc = new Docxtemplater(zip, {
            paragraphLoop: true,
            linebreaks: true
          });

          const formVal = this.personForm.value;

          // For placeholders in your template:
          doc.render({
            fName: formVal.fName || '',
            lName: formVal.lName || '',
            description: formVal.description || '',
            career: formVal.career || '',
            career2: formVal.career2 || '',
            career3: formVal.career3 || '',
            phoneNum: formVal.phoneNum || '',
            email: formVal.email || '',
            website: formVal.website || '',
            socialAccounts: formVal.socialAccounts,
            skills: formVal.skills || '',
            achievements: formVal.achievements || '',
            certifications: formVal.certifications || '',
            education: formVal.education,
            experience: formVal.experience,
            projects: formVal.projects,
            references: formVal.references
          });

          const out = doc.getZip().generate({
            type: 'blob',
            mimeType:
              'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
          });

          saveAs(out, 'original_resume.docx');
        } catch (err) {
          console.error('Error rendering template:', err);
        }
      }
    );
  }

  // *** (3) Improve Resume => calls AI endpoint
  improveResume() {
    if (!this.createdResumeId) {
      // Define message strings for the info dialog
      const infoTitle = 'Resume Required';
      const infoMessage = 'Please save your resume first before enhancing it.';
      const saveButtonText = 'Save Resume';
      
      this.showInfo(
        this.translatedTexts[infoTitle] || infoTitle,
        this.translatedTexts[infoMessage] || infoMessage,
        this.translatedTexts[saveButtonText] || saveButtonText,
        'fa-save',
        () => this.onSubmit()
      );
      return;
    }
    this.isImproving = true;

    // Define message strings for success and error cases
    const successTitle = 'Resume Enhanced';
    const successMessage = 'Your resume has been improved with AI technology.';
    const errorTitle = 'Enhancement Failed';
    const errorMessage = 'We encountered a problem while enhancing your resume.';

    this.appService.improveResume(this.createdResumeId).subscribe({
      next: (res) => {
        console.log('AI improved resume:', res);
        this.isImproving = false;
        this.enhancedResumeText = res.ai_enhanced_resume;
        this.atsScore = res.ats_score;
        
        // Use translated strings if available, otherwise use default English
        this.showSuccess(
          this.translatedTexts[successTitle] || successTitle,
          this.translatedTexts[successMessage] || successMessage,
          false,
          true
        );
        this.currentStep = 3;
      },
      error: (err) => {
        console.error('Failed to improve resume:', err);
        this.isImproving = false;
        
        // Use translated strings if available, otherwise use default English
        this.showError(
          this.translatedTexts[errorTitle] || errorTitle,
          this.translatedTexts[errorMessage] || errorMessage,
          err.message || 'Unknown error',
          () => this.improveResume() // Retry action
        );
      }
    });
  }

  // *** (4) Download Enhanced => docxtemplater using the AI text
  downloadEnhancedDocx() {
    if (!this.enhancedResumeText) {
      this.showInfo(
        'Enhancement Required',
        'Please enhance your resume with AI before downloading the enhanced version.',
        'Enhance Now',
        'fa-magic',
        () => this.improveResume()
      );
      return;
    }

    loadFile(
      '../assets/doc-templates/Resume-2.docx',
      (error, content) => {
        if (error) {
          console.error('Error loading template file:', error);
          return;
        }
        try {
          const zip = new PizZip(content);
          const doc = new Docxtemplater(zip, {
            paragraphLoop: true,
            linebreaks: true
          });

          // Suppose the LLM just returns one big text block in 'ai_enhanced_resume'.
          // If it's structured text, you might parse it or do something fancier.
          // For now, let's just place it in a single placeholder, e.g. {improvedResume}

          doc.render({
            improvedResume: this.enhancedResumeText,
            atsScore: this.atsScore || 0
          });

          const out = doc.getZip().generate({
            type: 'blob',
            mimeType:
              'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
          });

          saveAs(out, 'enhanced_resume.docx');
          this.currentStep = 4; 
        } catch (err) {
          console.error('Error rendering template (enhanced):', err);
        }
      }
    );
  }
}