# 🎯 Synapse Demo Guide

## 🚀 Quick Demo Setup

### **1. Open Demo Interface**
- Open `demo.html` in any web browser
- Or visit the live demo at your GitHub Pages URL

### **2. Test Scenarios**

#### **High Priority Lead**
```
Sarah Johnson, VP Engineering at TechCorp, needs CRM for 500+ team. Budget approved $100k. Contact: sarah.j@techcorp.com
```
**Expected AI Response:**
- Priority: High
- Action: Web scraping + CRM creation
- Notifications: Immediate alerts

#### **Investment Research**
```
Need Tesla stock analysis for $2M portfolio decision. Urgent market outlook required.
```
**Expected AI Response:**
- Domain: Investment
- Action: Financial data scraping
- Output: Investment brief

#### **Low Priority**
```
Hi, I'm a student researching CRM options for a project. Can you send information? Email: student@gmail.com
```
**Expected AI Response:**
- Priority: Low
- Action: Basic CRM record only
- Reasoning: Academic inquiry

### **3. Monitor Results**
- **Slack**: Check configured channel for notifications
- **Email**: Check inbox for intelligent alerts
- **CRM**: Login to SuiteCRM to see created records
- **Logs**: AWS CloudWatch for detailed processing

### **4. Demo Flow**
1. **Input**: Enter inquiry in demo form
2. **Processing**: Watch AI analysis animation
3. **Results**: See completion message
4. **Verification**: Check notification channels

## 🎬 **Demo Script**

### **Opening (30 seconds)**
"This is Synapse - an AI agent that transforms raw business inquiries into intelligent insights. Watch as I enter a simple email and see how AI analyzes, prioritizes, and processes it."

### **Demo (60 seconds)**
1. Enter high-priority lead example
2. Show processing animation
3. Explain AI decision-making
4. Show notifications received

### **Impact (30 seconds)**
"In 2 minutes, Synapse analyzed the inquiry, researched the company, created an enriched CRM record, and alerted the right team members. This saves hours of manual work while ensuring no leads are missed."

## 📊 **Key Demo Points**

- **AI Reasoning**: Not just data processing
- **Multi-Domain**: Works across industries
- **Real-Time**: Live web intelligence
- **Production Ready**: Enterprise architecture
- **Intelligent Routing**: Smart prioritization

## 🔧 **Troubleshooting**

### **If Demo Form Doesn't Work:**
- Check network connection
- Verify webhook URL is accessible
- Use browser developer tools to check console

### **If No Notifications:**
- Verify Slack webhook URL is configured
- Check email verification in SES
- Confirm CRM credentials are valid

### **Rate Limiting:**
- Wait 10-15 minutes between tests
- Use different example scenarios
- Check CloudWatch logs for details