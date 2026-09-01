\# Construction of Benchmark Datasets for Neuro-Symbolic Legal Reasoning



This repository contains code, prompts, validation utilities, and benchmark outputs developed during a Summer Research Internship at the Department of Computer Science and Engineering, IIT Kharagpur.



\## Project Overview



The project focuses on constructing structured benchmark datasets for neuro-symbolic legal reasoning. Statutory text is converted into machine-interpretable representations consisting of:



\- variables

\- grounded predicates

\- logical rules

\- supporting statutory spans

\- validation reports

\- JSON and Excel outputs



The work primarily covers the SARA dataset and extends the benchmark generation methodology to the COLIEE dataset.



\## Repository Structure



```text

benchmark\_sara\_logic/

&#x20;   SARA benchmark generation pipeline, prompts, validation logic, and final outputs.



benchmark\_coliee\_v3/

&#x20;   Automated COLIEE benchmark generation pipeline, prompts, validation logic, reports, and exported outputs.



data/

&#x20;   Input statutory datasets used by the benchmark generation pipelines.



src/

&#x20;   Shared helper utilities such as LLM client and common processing functions.



docs/

&#x20;   Report and supporting documentation.



sample\_outputs/

&#x20;   Selected benchmark artifacts for quick inspection.

