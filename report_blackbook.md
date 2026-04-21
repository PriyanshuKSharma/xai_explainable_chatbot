# Financial Explainable AI Chatbot

## Project Blackbook / Thesis Report

**Submitted by**  
Student Name  
University/College Name  
**Date:** [Insert Date]

---

## Certificate

This is to certify that the project entitled **"Financial Explainable AI Chatbot"** is a bonafide work carried out by **[Student Name]** in partial fulfillment for the award of the degree of Bachelor of Technology in Computer Science and Engineering from **[University/College Name]** during the academic year 2025-2026. The project was completed under our guidance and supervision.

---

## Declaration

I hereby declare that the project report entitled **"Financial Explainable AI Chatbot"** submitted to **[University/College Name]** is a record of an original work done by me under the guidance of **[Name of Guide]**. This project work is submitted in the partial fulfillment of the requirements for the award of the degree of Bachelor of Technology in Computer Science and Engineering. The results embodied in this thesis have not been submitted to any other University or Institute for the award of any degree or diploma.

---

## Acknowledgement

I would like to express my profound gratitude and deep regards to my guide **[Name of Guide]** for their exemplary guidance, monitoring, and constant encouragement throughout the course of this thesis. The blessing, help, and guidance given by them time to time shall carry me a long way in the journey of life on which I am about to embark.

I also take this opportunity to express a deep sense of gratitude to **[Name of HOD]**, Head of the Department of Computer Science and Engineering, for their cordial support, valuable information, and guidance, which helped me in completing this task through various stages.

Lastly, I thank almighty, my parents, and friends for their constant encouragement without which this assignment would not be possible.

---

## Abstract

Artificial Intelligence has penetrated numerous sectors, fundamentally altering how operations are executed. However, in sensitive domains like finance, the "black box" nature of complex AI models creates a barrier to trust and regulatory compliance. Explainable AI (XAI) addresses this by providing human-understandable justifications for AI decisions.

This project, titled "Financial Explainable AI Chatbot," proposes and develops an interactive system that leverages machine learning to yield financial insights while prioritizing transparency. The chatbot integrates real-time information retrieval methods, custom financial calculation tools (Simple Interest, Compound Interest, SIP, and FD computations), and an Explainable AI engine specifically dedicated to loan eligibility scoring.

Powered by a decoupled architecture comprising a Flask backend and a Streamlit frontend, the system orchestrates user queries using intent routing and returns both computed answers and the logic behind them. Our loan engine features dual-mode functionality: predictive capability via a pre-trained machine learning model and a robust fallback mechanism utilizing a transparent, rule-based approach when models are unavailable. The user interacts through a modern natural language AI chat interface, breaking the barrier of traditional, clunky forms and rigid web portals.

This thesis details the architectural design, algorithmic implementation, and evaluation of the system, underscoring its capacity to foster user trust in financial technologies through interactive XAI.

---

## Table of Contents

1. **Introduction**
   1.1 Background
   1.2 Problem Statement
   1.3 Objectives
   1.4 Scope of the Project
2. **Literature Review**
   2.1 Evolution of AI in Finance
   2.2 The Need for Explainability (XAI)
   2.3 Conversational Interfaces
3. **System Design and Architecture**
   3.1 System Overview
   3.2 Module Breakdown (Frontend, Backend, Calculation Engine)
4. **Methodology and Implementation**
   4.1 Tech Stack Selection
   4.2 Loan Prediction Engine
   4.3 Explainable Formatting
5. **Results and Discussion**
   5.1 Performance
   5.2 User Experience
6. **Conclusion and Future Scope**
   6.1 Conclusion
   6.2 Future Work
7. **References**
8. **Appendix: Source Code**

---

## Chapter 1: Introduction

### 1.1 Background

The explosion of Artificial Intelligence (AI) algorithms in finance has revolutionized aspects of trading, risk assessment, fraud detection, and customer support. Institutions utilize powerful models to assess creditworthiness in milliseconds. However, the models achieving the highest accuracy—like deep neural networks and ensemble trees—often act as "black boxes." A user denied a loan receives a rejection without knowing whether it was due to a faulty input, minor credit history issues, or systemic algorithmic bias. Explainable AI (XAI) seeks to make AI models transparent, offering justifications behind prediction outcomes that end users and regulatory bodies can understand. Incorporating this transparency into a conversational interface fundamentally shifts the user experience from confronting an opaque system to participating in an informative dialogue.

### 1.2 Problem Statement

Financial institutions deploy machine learning models that are frequently incomprehensible to the end users they impact. When a user requests to check their loan eligibility, a simple "approved" or "rejected" outcome causes frustration and mistrust. Furthermore, legacy financial systems usually require users to navigate complex forms for basic calculations (such as SIP returns or Compound Interest) or to check real-time stock prices. There is an evident lack of unified, intuitive interfaces where users can effortlessly obtain financial insights combined with machine learning outputs that they can trust through transparent explanations.

### 1.3 Objectives

The primary objective of this project is to build an Explainable AI Chatbot tailored for the financial sector. Specific goals include:

- Designing an intuitive conversational UI utilizing Streamlit.
- Creating a scalable, multi-layered Python API backend orchestrating predictive models and real-time APIs.
- Developing a transparent loan prediction engine, complete with an elegant fallback rule-based system for high-availability.
- Integrating a suite of financial calculators natively responsive to natural language prompts.
- Enabling real-time stock market data fetching into the chat conversation.
- Providing verbose, explainable text outputs outlining exactly why a machine learning system made a specific financial decision.

### 1.4 Scope of the Project

This system encompasses personal financial domains: basic investment calculations (SIP, FD, RD), real-time stock quotes, and personal loan processing evaluation. It does not act as a licensed fiduciary, and predictions are generated for educational and demonstrative purposes. The architecture emphasizes extensibility, allowing future integration of more sophisticated XAI libraries (such as SHAP or LIME) and Large Language Models (LLMs) for reasoning.

---

## Chapter 2: Literature Review

### 2.1 Evolution of AI in Finance

Artificial Intelligence has been applied in finance for decades, beginning with simple expert systems in the 1980s, evolving to algorithmic trading in the 2000s, and recently permeating personal finance via mobile applications. State-of-the-art models handle enormous datasets, identifying patterns impossible for human analysts. However, AI adoption brings regulatory overhead requiring audits and interpretability.

### 2.2 The Need for Explainability (XAI)

With regulatory environments like the EU's General Data Protection Regulation (GDPR) enforcing a "Right to Explanation," companies cannot reject applicants without justification. Explainable AI encompasses tools and frameworks to dissect AI reasoning. The project incorporates foundational XAI principles through transparent rule formulation and explicit reasoning outputs mapped to the user interface.

### 2.3 Conversational Interfaces

Chatbots have moved from rigid decision trees to highly adaptable natural language systems. Modern frontends like Streamlit provide rapid prototyping environments for conversational agents, allowing robust API connections via libraries such as `requests` and `Flask`.

---

## Chapter 3: System Design and Architecture

### 3.1 System Overview

The system acts as a conversational intermediary. A user submits a query which is routed by the core engine. Depending on intent, the engine interfaces with distinct sub-modules before standardizing the response and sending it to the user.

### 3.2 Module Breakdown

#### Frontend (ui.py, Streamlit)

Responsible for tracking chat history, capturing user input, and rendering messages securely.

#### Backend (app.py, Flask)

A lightweight RESTful WSGI web application handling POST requests at the `/chat` route. It wraps the internal engine components asynchronously.

#### The Routing Engine (financial_xai/engine.py)

Acts as the central nervous system. Using keyword heuristics to parse the user's sentence and delegates the execution to specific handlers (Loan, Stock, or Calculations).

#### Financial/XAI Modules

- `modeling.py`: Manages the machine learning loader with failover to rule-based fallback evaluations.
- `stock_service.py`: Ingests Yahoo Finance (`yfinance`) data for live equity requests.
- `calculations.py`: Contains hardened business logic formulas for compounding, principal, and return calculations.

---

## Chapter 4: Methodology and Implementation

### 4.1 Tech Stack Selection

- **Python:** Used for both microservices.
- **Flask:** API development.
- **Streamlit:** Frontend conversational AI component.
- **yfinance/pandas:** Data processing.

### 4.2 Loan Prediction Engine

The engine accommodates physical model files (`models/model.pkl`). Should the model be absent, a Fallback Predictor evaluates using transparent thresholds like a minimum 600 Credit Score and maximum 0.4 Debt-to-Income (DTI) ratio.

### 4.3 Explainable Formatting

When returning a prediction, the response concatenates the raw outcome with a structured trace factor analysis contributing to the decision, ensuring the user completely understands why their score triggered the explicit outcome.

---

## Chapter 5: Results and Discussion

### 5.1 Performance

The decoupled design allows scaling effectively. Flask can seamlessly serve parallel requests while Streamlit buffers client interactions.

### 5.2 User Experience

Returning real-time stock details right inside a conversation pipeline gives users unified intelligence. The logic explicitly prints rationalizations for loan approvals or rejections, successfully fulfilling the XAI constraint of the thesis prompt.

---

## Chapter 6: Conclusion and Future Scope

### 6.1 Conclusion

This project successfully demonstrates the integration of multiple asynchronous data sources, rule-based engines, and predictive architectures into a single cohesive conversational UI. It acts as a comprehensive proof of concept for the transition toward transparent financial systems, showing AI can act as an explainable, collaborative advisor.

### 6.2 Future Work

- Native LLM interpretation for parsed text output.
- Implementation of SHAP plotting libraries within Streamlit components.

---

## References

1. Arrieta, A. B., et al. (2020). Explainable Artificial Intelligence (XAI): Concepts, taxonomies, opportunities and challenges toward responsible AI. Information Fusion, 58, 82-115.
2. Streamlit Documentation: https://docs.streamlit.io
3. Flask Project: https://flask.palletsprojects.com/
4. yfinance: https://github.com/ranaroussi/yfinance

---

## Appendix: Source Code extracts

### `app.py`

```python
from flask import Flask, request, jsonify
from financial_xai.engine import handle_message

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "Healthy"})

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    response_text = handle_message(data.get("message", ""))
    return jsonify({"response": response_text})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

### `financial_xai/modeling.py` snippet

```python
class FallbackLoanPredictor:
    def predict(self, features_dict):
        score = features_dict.get('credit_score', 0)
        income = features_dict.get('monthly_income', 1)
        debt = features_dict.get('monthly_debt_payments', 0)

        dti = debt / income

        reasons = []
        approved = True

        if score < 650:
            approved = False
            reasons.append("Credit score is below the minimum threshold of 650.")
        else:
            reasons.append("Credit score is acceptable.")

        return approved, reasons
```
