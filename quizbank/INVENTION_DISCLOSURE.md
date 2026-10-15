# What is new in this project (for your IP cell)

This is a plain description of the method, not legal advice. Whether something can be patented depends
on the law of the country (in India, "computer programmes per se" and mere methods of teaching are excluded
under Section 3(k) and 3(m) of the Patents Act, so a pure software claim usually fails; a claim tied to a
specific technical effect has a better chance). Ask your college IP cell or a patent agent before you publish
or demonstrate it widely, because publishing first can destroy novelty. Copyright on your own code exists
automatically, and registering it is cheap.

## The combined method

1. **Confidence-calibrated marking.** Each answer is submitted with a confidence level (guessing / fairly sure / certain).
   The system keeps the ordinary score but also computes a calibration score = 100 x (1 - Brier score) using the claimed
   probabilities 0.33 / 0.66 / 0.95. A "certain" answer that is wrong is flagged as a likely misconception and sent to revision.
2. **Misconception-driven spaced repetition.** Wrong answers enter Leitner boxes (1, 2, 4, 8, 16 days). Confidently wrong answers
   are reported separately to the student.
3. **Adaptive practice using topic mastery.** The next question is chosen from the student's weakest topic (accuracy from practice and
   quizzes together) at a difficulty derived from the last six answers.
4. **Self-correcting question bank.** Item analysis computes the difficulty index and the upper/lower 27% discrimination index from
   real attempts, and flags questions whose labelled difficulty disagrees with measured difficulty or that do not separate strong from
   weak students.
5. **Server-enforced, per-student papers.** Question and option order are derived from the attempt id, the deadline is kept on the server
   with a grace period, and late attempts are excluded from rankings.

Each idea alone is known in the literature (Brier score, Leitner system, item response theory, classical item analysis).
The possibly novel part is the combination, and in particular using confidently-wrong answers as the trigger that links marking,
revision scheduling and adaptive topic selection. A prior-art search is needed before any claim of novelty is made.
