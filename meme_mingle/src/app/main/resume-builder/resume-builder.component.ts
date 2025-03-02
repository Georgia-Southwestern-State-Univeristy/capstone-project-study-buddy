import { Component } from '@angular/core';
import Docxtemplater from 'docxtemplater';
import PizZip from 'pizzip';
import PizZipUtils from 'pizzip/utils/index.js';
import { saveAs } from 'file-saver';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

function loadFile(url: string, callback: { (error: Error | null, content: string): void; (err: Error, data: string): void; }) {
  PizZipUtils.getBinaryContent(url, callback);
}
@Component({
  selector: 'app-resume-builder',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './resume-builder.component.html',
  styleUrls: ['./resume-builder.component.scss']
})
export class ResumeBuilderComponent {

  personForm = new FormGroup({
    fName: new FormControl(""),
    lName: new FormControl(""),
    career: new FormControl(""),
    career2: new FormControl(""),
    career3: new FormControl(""),
    phoneNum: new FormControl(""),
    description: new FormControl(""),
    socialmedia: new FormControl(""),
    email: new FormControl(""),
    website: new FormControl(""),
    skills: new FormControl(""),
    school: new FormControl(""),
    grad: new FormControl(""),
    major: new FormControl(""),
    exp_company: new FormControl(""),
    exp_date: new FormControl(""),
    exp_description: new FormControl(""),
  });

  generate() {
    loadFile(
      '../assets/doc-templates/Color-block-resume.docx',
      (error: Error | null, content: string) => {
        if (error) {
          console.error('Error loading file:', error);
          return; // Stop further processing if error occurs
        }
        try {
          const zip = new PizZip(content);
          const doc = new Docxtemplater(zip, {
            paragraphLoop: true,
            linebreaks: true,
          });
  
          // Make sure the keys passed here match those in the template
          doc.render({
            fName: this.personForm.value.fName || 'N/A',  // Provide default if empty
            lName: this.personForm.value.lName || 'N/A',
            career: this.personForm.value.career || '',    // Provide default if empty
            career2: this.personForm.value.career2 || '', 
            career3: this.personForm.value.career3 || '', 
            phoneNum: this.personForm.value.phoneNum || 'N/A', // Provide default if empty
            description: this.personForm.value.description || 'N/A',
            socialmedia: this.personForm.value.socialmedia || 'N/A', 
            email: this.personForm.value.email || 'N/A',
            website: this.personForm.value.website || 'N/A', 
            skills: this.personForm.value.skills || '',
            school: this.personForm.value.school || 'N/A', 
            graduationdate: this.personForm.value.grad || 'N/A',
            major: this.personForm.value.major || 'N/A',
            exp_company: this.personForm.value.exp_company || 'N/A', 
            exp_date: this.personForm.value.exp_date || 'N/A',
            exp_description: this.personForm.value.exp_description || 'N/A'
          });
  
          const out = doc.getZip().generate({
            type: 'blob',
            mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          });
  
          saveAs(out, 'GSW_resume.docx');
        } catch (err) {
          console.error('Error rendering the template:', err);
        }
      }
    );
  }

onSubmit() {
  console.log(this.personForm.value);
}



}
