# Notes 

**1.** Add network analysis 
**2.** Add option to choose different models 
**3.** Add option to extract victim data
**4.** Add option to process long documents 
**5.** Add option to classify docs 
**6.** Add option to adjust prompt
**7.** explore the 10-15 page window. Can we go larger or smaller? And does it work for osm
**8.** create the option for the user to adjust the summary prompt. Based on the changes made to the summary prompt, use a team of agents to adjust the other prompts, namely the combine and coherence templates. 

**Quantitative metrics**
- BLEU, the simplest metric, calculates the degree of overlap between the reference and generated texts by considering 1- to 4-gram sequences;
- ROUGE-L evaluates similarity based on the longest common subsequence; 
- BERTScore, which leverages contextual BERT embeddings to evaluate the semantic similarity of the generated and reference texts;

- Completeness: “Which summary more completely captures important information?” This compares the summaries’ recall, i.e. the amount of clinically significant detail retained from the input text.
- Correctness: “Which summary includes less false information?” This compares the summaries’ precision, i.e. instances of fabricated information.
- Conciseness: “Which summary contains less non-important information?” This compares which summary is more condensed, as the value of a summary decreases with superfluous information.

**Flow**:
1. Doc classification. Determine whether the doc contains relevant pages. Set some threshold for which docs should be reviwed and which should be ignored.
2. OCR
3. Generate summaries of all docs. Determine if the docs can be further filtered (do we only want to iterate over certain pages? might optimize the flow)
4. Generate summary/timeline/extract entities 

**summary**
1. Process in batches. Can we disregard certain batches based on whether it contains relevant info when compared to the memory log?

**Next**
1. Generate timelines 
2. Mixture of models
3. Clean up UI interface for emails/attach PDFs to email 
4. Add MOA to vercel deployment 
5. Set up private endpoint 



**Pairwise Evaluations**
- https://blog.langchain.dev/pairwise-evaluations-with-langsmith/


**Citations**

**Papers**
1. https://arxiv.org/abs/2405.20362

2. https://arxiv.org/pdf/2309.07430

**Github**
1. https://github.com/Jeryi-Sun/LLM-and-Law

2. https://github.com/pengxiao-song/LaWGPT