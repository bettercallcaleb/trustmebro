# Review panel — seed 17

40 sample questions with reference answers. No model results. This file is for human review; do not feed the answer key to a model.

## core-depth/routing/v000/L1

Directed routes (only listed edges exist): A->B: time 2, toll 3; A->C: time 14, toll 2; A->D: time 13, toll 1; A->E: time 1, toll 3; A->F: time 10, toll 2; B->C: time 1, toll 3; B->D: time 10, toll 3; B->E: time 10, toll 2; B->F: time 3, toll 0; C->E: time 8, toll 0; C->F: time 4, toll 1; D->F: time 11, toll 3; E->F: time 8, toll 1. Travel from A to F. Minimize total time. Return the minimum total time as an integer.

**Oracle answer:** 5

## core-depth/routing/v000/L2

Directed routes (only listed edges exist): A->B: time 2, toll 3; A->C: time 14, toll 2; A->D: time 13, toll 1; A->E: time 1, toll 3; A->F: time 10, toll 2; B->C: time 1, toll 3; B->D: time 10, toll 3; B->E: time 10, toll 2; B->F: time 3, toll 0; C->E: time 8, toll 0; C->F: time 4, toll 1; D->F: time 11, toll 3; E->F: time 8, toll 1. Travel from A to F. Minimize total time. You must visit C. Return the minimum total time as an integer.

**Oracle answer:** 7

## core-depth/routing/v000/L3

Directed routes (only listed edges exist): A->B: time 2, toll 3; A->C: time 14, toll 2; A->D: time 13, toll 1; A->E: time 1, toll 3; A->F: time 10, toll 2; B->C: time 1, toll 3; B->D: time 10, toll 3; B->E: time 10, toll 2; B->F: time 3, toll 0; C->E: time 8, toll 0; C->F: time 4, toll 1; D->F: time 11, toll 3; E->F: time 8, toll 1. Travel from A to F. Minimize total time. You must visit C and total toll must be at most 4. Return the minimum total time as an integer.

**Oracle answer:** 18

## core-depth/routing/v000/L4

Directed routes (only listed edges exist): A->B: time 2, toll 3; A->C: time 14, toll 2; A->D: time 13, toll 1; A->E: time 1, toll 3; A->F: time 10, toll 2; B->C: time 1, toll 3; B->D: time 10, toll 3; B->E: time 10, toll 2; B->F: time 3, toll 0; C->E: time 8, toll 0; C->F: time 4, toll 1; D->F: time 11, toll 3; E->F: time 8, toll 1. Travel from A to F. Minimize total time. You must visit C, total toll must be at most 4, and two successive edges cannot both have positive toll. Return the minimum total time as an integer.

**Oracle answer:** 30

## core-depth/routing/v001/L1

Directed routes (only listed edges exist): A->B: time 8, toll 1; A->C: time 11, toll 2; A->D: time 7, toll 2; A->E: time 1, toll 2; A->F: time 15, toll 3; B->C: time 13, toll 0; B->D: time 4, toll 1; B->E: time 1, toll 1; B->F: time 14, toll 3; C->E: time 6, toll 0; C->F: time 4, toll 3; D->E: time 15, toll 2; D->F: time 15, toll 3; E->F: time 12, toll 2. Travel from A to F. Minimize total time. Return the minimum total time as an integer.

**Oracle answer:** 13

## core-depth/routing/v001/L2

Directed routes (only listed edges exist): A->B: time 8, toll 1; A->C: time 11, toll 2; A->D: time 7, toll 2; A->E: time 1, toll 2; A->F: time 15, toll 3; B->C: time 13, toll 0; B->D: time 4, toll 1; B->E: time 1, toll 1; B->F: time 14, toll 3; C->E: time 6, toll 0; C->F: time 4, toll 3; D->E: time 15, toll 2; D->F: time 15, toll 3; E->F: time 12, toll 2. Travel from A to F. Minimize total time. You must visit C. Return the minimum total time as an integer.

**Oracle answer:** 15

## core-depth/routing/v001/L3

Directed routes (only listed edges exist): A->B: time 8, toll 1; A->C: time 11, toll 2; A->D: time 7, toll 2; A->E: time 1, toll 2; A->F: time 15, toll 3; B->C: time 13, toll 0; B->D: time 4, toll 1; B->E: time 1, toll 1; B->F: time 14, toll 3; C->E: time 6, toll 0; C->F: time 4, toll 3; D->E: time 15, toll 2; D->F: time 15, toll 3; E->F: time 12, toll 2. Travel from A to F. Minimize total time. You must visit C and total toll must be at most 4. Return the minimum total time as an integer.

**Oracle answer:** 25

## core-depth/routing/v001/L4

Directed routes (only listed edges exist): A->B: time 8, toll 1; A->C: time 11, toll 2; A->D: time 7, toll 2; A->E: time 1, toll 2; A->F: time 15, toll 3; B->C: time 13, toll 0; B->D: time 4, toll 1; B->E: time 1, toll 1; B->F: time 14, toll 3; C->E: time 6, toll 0; C->F: time 4, toll 3; D->E: time 15, toll 2; D->F: time 15, toll 3; E->F: time 12, toll 2. Travel from A to F. Minimize total time. You must visit C, total toll must be at most 4, and two successive edges cannot both have positive toll. Return the minimum total time as an integer.

**Oracle answer:** 25

## core-depth/scheduling/v000/L1

Jobs: A (3,7,6,1,-); B (6,8,15,4,G); C (5,8,9,2,E); D (9,11,4,2,B); E (1,4,14,3,-); F (4,7,4,5,E); G (0,5,10,4,-); H (6,9,4,4,G). Fields are (start,end,reward,cost,prerequisite), with '-' meaning none. Select jobs on one machine; intervals [start,end) cannot overlap. Each job can be selected at most once. Maximize total reward. If no feasible selection exists, the answer is 0. Ignore cost and prerequisites. Return the optimal integer.

**Oracle answer:** 33

## core-depth/scheduling/v000/L2

Jobs: A (3,7,6,1,-); B (6,8,15,4,G); C (5,8,9,2,E); D (9,11,4,2,B); E (1,4,14,3,-); F (4,7,4,5,E); G (0,5,10,4,-); H (6,9,4,4,G). Fields are (start,end,reward,cost,prerequisite), with '-' meaning none. Select jobs on one machine; intervals [start,end) cannot overlap. Each job can be selected at most once. Maximize total reward. If no feasible selection exists, the answer is 0. Job H must be selected. Ignore cost and prerequisites. Return the optimal integer.

**Oracle answer:** 22

## core-depth/scheduling/v000/L3

Jobs: A (3,7,6,1,-); B (6,8,15,4,G); C (5,8,9,2,E); D (9,11,4,2,B); E (1,4,14,3,-); F (4,7,4,5,E); G (0,5,10,4,-); H (6,9,4,4,G). Fields are (start,end,reward,cost,prerequisite), with '-' meaning none. Select jobs on one machine; intervals [start,end) cannot overlap. Each job can be selected at most once. Maximize total reward. If no feasible selection exists, the answer is 0. Job H must be selected. Total cost must be at most 8. Ignore prerequisites. Return the optimal integer.

**Oracle answer:** 18

## core-depth/scheduling/v000/L4

Jobs: A (3,7,6,1,-); B (6,8,15,4,G); C (5,8,9,2,E); D (9,11,4,2,B); E (1,4,14,3,-); F (4,7,4,5,E); G (0,5,10,4,-); H (6,9,4,4,G). Fields are (start,end,reward,cost,prerequisite), with '-' meaning none. Select jobs on one machine; intervals [start,end) cannot overlap. Each job can be selected at most once. Maximize total reward. If no feasible selection exists, the answer is 0. Job H must be selected. Total cost must be at most 8. A selected job with a prerequisite requires that prerequisite to be selected and finished before or at its start. Return the optimal integer.

**Oracle answer:** 14

## core-depth/scheduling/v001/L1

Jobs: A (10,12,2,4,E); B (6,10,17,4,D); C (3,7,14,5,D); D (1,3,3,3,-); E (2,4,16,2,-); F (4,7,6,5,E); G (7,12,9,3,-); H (7,10,18,4,-). Fields are (start,end,reward,cost,prerequisite), with '-' meaning none. Select jobs on one machine; intervals [start,end) cannot overlap. Each job can be selected at most once. Maximize total reward. If no feasible selection exists, the answer is 0. Ignore cost and prerequisites. Return the optimal integer.

**Oracle answer:** 42

## core-depth/scheduling/v001/L2

Jobs: A (10,12,2,4,E); B (6,10,17,4,D); C (3,7,14,5,D); D (1,3,3,3,-); E (2,4,16,2,-); F (4,7,6,5,E); G (7,12,9,3,-); H (7,10,18,4,-). Fields are (start,end,reward,cost,prerequisite), with '-' meaning none. Select jobs on one machine; intervals [start,end) cannot overlap. Each job can be selected at most once. Maximize total reward. If no feasible selection exists, the answer is 0. Job C must be selected. Ignore cost and prerequisites. Return the optimal integer.

**Oracle answer:** 37

## core-depth/scheduling/v001/L3

Jobs: A (10,12,2,4,E); B (6,10,17,4,D); C (3,7,14,5,D); D (1,3,3,3,-); E (2,4,16,2,-); F (4,7,6,5,E); G (7,12,9,3,-); H (7,10,18,4,-). Fields are (start,end,reward,cost,prerequisite), with '-' meaning none. Select jobs on one machine; intervals [start,end) cannot overlap. Each job can be selected at most once. Maximize total reward. If no feasible selection exists, the answer is 0. Job C must be selected. Total cost must be at most 8. Ignore prerequisites. Return the optimal integer.

**Oracle answer:** 23

## core-depth/scheduling/v001/L4

Jobs: A (10,12,2,4,E); B (6,10,17,4,D); C (3,7,14,5,D); D (1,3,3,3,-); E (2,4,16,2,-); F (4,7,6,5,E); G (7,12,9,3,-); H (7,10,18,4,-). Fields are (start,end,reward,cost,prerequisite), with '-' meaning none. Select jobs on one machine; intervals [start,end) cannot overlap. Each job can be selected at most once. Maximize total reward. If no feasible selection exists, the answer is 0. Job C must be selected. Total cost must be at most 8. A selected job with a prerequisite requires that prerequisite to be selected and finished before or at its start. Return the optimal integer.

**Oracle answer:** 17

## core-depth/ledger/v000/L1

Initial balances A=21, B=12; initially held=0 in both accounts. ADD increases balance. SPEND reduces balance if enough available funds exist. Available equals balance. A failed operation has no effect. Execute these brackets in order: [SPEND A 3]; [SPEND A 11]; [SPEND A 8]; [SPEND A 11]; [SPEND A 13]; [SPEND A 12]; [ADD A 5]; [SPEND A 7]. Return A's final available funds as an integer.

**Oracle answer:** 5

## core-depth/ledger/v000/L2

Initial balances A=21, B=12; initially held=0 in both accounts. ADD increases balance. SPEND reduces balance if enough available funds exist. Available = balance minus held. HOLD increases held if enough available. RELEASE reduces held if enough held. A failed operation has no effect. Execute these brackets in order: [SPEND A 10]; [RELEASE A 5]; [SPEND A 12]; [RELEASE A 8]; [HOLD A 9]; [HOLD A 3]; [ADD A 4]; [HOLD A 4]. Return A's final available funds as an integer.

**Oracle answer:** 2

## core-depth/ledger/v000/L3

Initial balances A=21, B=12; initially held=0 in both accounts. ADD increases balance. SPEND reduces balance if enough available funds exist. Available = balance minus held. HOLD increases held if enough available. RELEASE reduces held if enough held. TRANSFER source n destination reduces the source balance and increases the destination balance by n if the source has enough available; holds do not move. A failed operation has no effect. Execute these brackets in order: [HOLD A 2]; [RELEASE B 7]; [SPEND B 10]; [SPEND A 11]; [ADD A 2]; [TRANSFER B 4 A]; [TRANSFER B 5 A]; [HOLD B 9]. Return A's final available funds as an integer.

**Oracle answer:** 10

## core-depth/ledger/v000/L4

Initial balances A=21, B=12; initially held=0 in both accounts. ADD increases balance. SPEND reduces balance if enough available funds exist. Available = balance minus held. HOLD increases held if enough available. RELEASE reduces held if enough held. TRANSFER source n destination reduces the source balance and increases the destination balance by n if the source has enough available; holds do not move. Each bracket is atomic: if any operation fails, undo all operations in that bracket; proceed to next bracket. Execute these brackets in order: [HOLD B 7]; [ADD A 2, RELEASE B 11]; [SPEND B 4, HOLD B 9]; [RELEASE B 3, HOLD B 8, ADD B 12]; [HOLD B 8]; [RELEASE B 11, HOLD A 11, TRANSFER A 10 B]; [RELEASE B 11, TRANSFER A 9 B]; [ADD B 9]. Return A's final available funds as an integer.

**Oracle answer:** 0

## core-depth/ledger/v001/L1

Initial balances A=19, B=13; initially held=0 in both accounts. ADD increases balance. SPEND reduces balance if enough available funds exist. Available equals balance. A failed operation has no effect. Execute these brackets in order: [SPEND A 12]; [SPEND A 2]; [SPEND A 2]; [SPEND A 4]; [SPEND A 7]; [ADD A 6]; [SPEND A 13]; [SPEND A 12]. Return A's final available funds as an integer.

**Oracle answer:** 9

## core-depth/ledger/v001/L2

Initial balances A=19, B=13; initially held=0 in both accounts. ADD increases balance. SPEND reduces balance if enough available funds exist. Available = balance minus held. HOLD increases held if enough available. RELEASE reduces held if enough held. A failed operation has no effect. Execute these brackets in order: [RELEASE A 5]; [ADD A 10]; [RELEASE A 3]; [HOLD A 10]; [RELEASE A 4]; [RELEASE A 10]; [HOLD A 9]; [SPEND A 7]. Return A's final available funds as an integer.

**Oracle answer:** 7

## core-depth/ledger/v001/L3

Initial balances A=19, B=13; initially held=0 in both accounts. ADD increases balance. SPEND reduces balance if enough available funds exist. Available = balance minus held. HOLD increases held if enough available. RELEASE reduces held if enough held. TRANSFER source n destination reduces the source balance and increases the destination balance by n if the source has enough available; holds do not move. A failed operation has no effect. Execute these brackets in order: [TRANSFER A 11 B]; [HOLD B 6]; [TRANSFER B 9 A]; [RELEASE A 9]; [ADD B 8]; [ADD B 3]; [ADD B 9]; [HOLD A 5]. Return A's final available funds as an integer.

**Oracle answer:** 12

## core-depth/ledger/v001/L4

Initial balances A=19, B=13; initially held=0 in both accounts. ADD increases balance. SPEND reduces balance if enough available funds exist. Available = balance minus held. HOLD increases held if enough available. RELEASE reduces held if enough held. TRANSFER source n destination reduces the source balance and increases the destination balance by n if the source has enough available; holds do not move. Each bracket is atomic: if any operation fails, undo all operations in that bracket; proceed to next bracket. Execute these brackets in order: [HOLD A 7, SPEND B 11, TRANSFER B 12 A]; [RELEASE B 5]; [TRANSFER A 8 B]; [TRANSFER B 9 A]; [TRANSFER B 9 A]; [TRANSFER B 12 A]; [TRANSFER A 4 B, TRANSFER B 3 A, TRANSFER A 7 B]; [ADD A 11, HOLD B 9]. Return A's final available funds as an integer.

**Oracle answer:** 32

## core-depth/relational/v000/L1

Users (id,group,status): A Z active; B Y active; C Z active; D Y active; E X active; F Z active; G Z active; H Z active. Events (user,sequence,amount,status): A 1 6 paid; A 2 8 paid; A 3 1 void; A 4 20 paid; B 1 16 paid; B 2 18 paid; C 1 8 paid; C 2 12 paid; D 1 17 paid; D 2 15 paid; E 1 24 void; E 2 13 paid; E 3 14 paid; F 1 19 paid; F 2 25 paid; F 3 22 paid; G 1 9 void; G 2 9 paid; H 1 7 paid; H 2 21 paid. Sum amounts of all paid events with amount >=5. Return the resulting integer.

**Oracle answer:** 250

## core-depth/relational/v000/L2

Users (id,group,status): A Z active; B Y active; C Z active; D Y active; E X active; F Z active; G Z active; H Z active. Events (user,sequence,amount,status): A 1 6 paid; A 2 8 paid; A 3 1 void; A 4 20 paid; B 1 16 paid; B 2 18 paid; C 1 8 paid; C 2 12 paid; D 1 17 paid; D 2 15 paid; E 1 24 void; E 2 13 paid; E 3 14 paid; F 1 19 paid; F 2 25 paid; F 3 22 paid; G 1 9 void; G 2 9 paid; H 1 7 paid; H 2 21 paid. Sum amounts of all paid events with amount >=5 belonging to active users. Return the resulting integer.

**Oracle answer:** 250

## core-depth/relational/v000/L3

Users (id,group,status): A Z active; B Y active; C Z active; D Y active; E X active; F Z active; G Z active; H Z active. Events (user,sequence,amount,status): A 1 6 paid; A 2 8 paid; A 3 1 void; A 4 20 paid; B 1 16 paid; B 2 18 paid; C 1 8 paid; C 2 12 paid; D 1 17 paid; D 2 15 paid; E 1 24 void; E 2 13 paid; E 3 14 paid; F 1 19 paid; F 2 25 paid; F 3 22 paid; G 1 9 void; G 2 9 paid; H 1 7 paid; H 2 21 paid. For each user, first retain only the event with largest sequence, regardless of status. Then sum amounts of retained paid events with amount >=5 belonging to active users. Return the resulting integer.

**Oracle answer:** 131

## core-depth/relational/v000/L4

Users (id,group,status): A Z active; B Y active; C Z active; D Y active; E X active; F Z active; G Z active; H Z active. Events (user,sequence,amount,status): A 1 6 paid; A 2 8 paid; A 3 1 void; A 4 20 paid; B 1 16 paid; B 2 18 paid; C 1 8 paid; C 2 12 paid; D 1 17 paid; D 2 15 paid; E 1 24 void; E 2 13 paid; E 3 14 paid; F 1 19 paid; F 2 25 paid; F 3 22 paid; G 1 9 void; G 2 9 paid; H 1 7 paid; H 2 21 paid. For each user, first retain only the event with largest sequence, regardless of status. Keep retained paid events with amount >=5 belonging to active users. Sum amounts within each group. Exclude any group containing any blocked user, even if that user has no qualifying event. Also exclude groups with total below 18. Sum the remaining group totals. Return the resulting integer.

**Oracle answer:** 117

## core-depth/relational/v001/L1

Users (id,group,status): A Y active; B X active; C Y blocked; D Y active; E X active; F Z active; G X active; H Z active. Events (user,sequence,amount,status): A 1 21 paid; A 2 26 void; B 1 9 paid; B 2 2 paid; C 1 2 paid; C 2 13 paid; D 1 7 paid; D 2 12 paid; D 3 16 paid; D 4 23 paid; E 1 13 paid; E 2 25 paid; E 3 20 void; F 1 7 paid; F 2 12 paid; F 3 14 paid; F 4 27 paid; G 1 2 paid; G 2 3 paid; G 3 27 paid; H 1 2 void; H 2 8 void. Sum amounts of all paid events with amount >=5. Return the resulting integer.

**Oracle answer:** 226

## core-depth/relational/v001/L2

Users (id,group,status): A Y active; B X active; C Y blocked; D Y active; E X active; F Z active; G X active; H Z active. Events (user,sequence,amount,status): A 1 21 paid; A 2 26 void; B 1 9 paid; B 2 2 paid; C 1 2 paid; C 2 13 paid; D 1 7 paid; D 2 12 paid; D 3 16 paid; D 4 23 paid; E 1 13 paid; E 2 25 paid; E 3 20 void; F 1 7 paid; F 2 12 paid; F 3 14 paid; F 4 27 paid; G 1 2 paid; G 2 3 paid; G 3 27 paid; H 1 2 void; H 2 8 void. Sum amounts of all paid events with amount >=5 belonging to active users. Return the resulting integer.

**Oracle answer:** 213

## core-depth/relational/v001/L3

Users (id,group,status): A Y active; B X active; C Y blocked; D Y active; E X active; F Z active; G X active; H Z active. Events (user,sequence,amount,status): A 1 21 paid; A 2 26 void; B 1 9 paid; B 2 2 paid; C 1 2 paid; C 2 13 paid; D 1 7 paid; D 2 12 paid; D 3 16 paid; D 4 23 paid; E 1 13 paid; E 2 25 paid; E 3 20 void; F 1 7 paid; F 2 12 paid; F 3 14 paid; F 4 27 paid; G 1 2 paid; G 2 3 paid; G 3 27 paid; H 1 2 void; H 2 8 void. For each user, first retain only the event with largest sequence, regardless of status. Then sum amounts of retained paid events with amount >=5 belonging to active users. Return the resulting integer.

**Oracle answer:** 77

## core-depth/relational/v001/L4

Users (id,group,status): A Y active; B X active; C Y blocked; D Y active; E X active; F Z active; G X active; H Z active. Events (user,sequence,amount,status): A 1 21 paid; A 2 26 void; B 1 9 paid; B 2 2 paid; C 1 2 paid; C 2 13 paid; D 1 7 paid; D 2 12 paid; D 3 16 paid; D 4 23 paid; E 1 13 paid; E 2 25 paid; E 3 20 void; F 1 7 paid; F 2 12 paid; F 3 14 paid; F 4 27 paid; G 1 2 paid; G 2 3 paid; G 3 27 paid; H 1 2 void; H 2 8 void. For each user, first retain only the event with largest sequence, regardless of status. Keep retained paid events with amount >=5 belonging to active users. Sum amounts within each group. Exclude any group containing any blocked user, even if that user has no qualifying event. Also exclude groups with total below 18. Sum the remaining group totals. Return the resulting integer.

**Oracle answer:** 54

## core-depth/constraints/v000/L1

Arrange A,B,C,D,E,F into slots 1 through 6, each used exactly once. Before means a smaller slot number. Rules: F is before E; A is before E; E is before D. How many distinct arrangements satisfy every rule? Return the count as an integer.

**Oracle answer:** 60

## core-depth/constraints/v000/L2

Arrange A,B,C,D,E,F into slots 1 through 6, each used exactly once. Before means a smaller slot number. Rules: F is before E; A is before E; E is before D; D and B occupy adjacent slots. How many distinct arrangements satisfy every rule? Return the count as an integer.

**Oracle answer:** 20

## core-depth/constraints/v000/L3

Arrange A,B,C,D,E,F into slots 1 through 6, each used exactly once. Before means a smaller slot number. Rules: F is before E; A is before E; E is before D; D and B occupy adjacent slots; F is not in slot 6; A and B do not occupy adjacent slots. How many distinct arrangements satisfy every rule? Return the count as an integer.

**Oracle answer:** 20

## core-depth/constraints/v000/L4

Arrange A,B,C,D,E,F into slots 1 through 6, each used exactly once. Before means a smaller slot number. Rules: F is before E; A is before E; E is before D; D and B occupy adjacent slots; F is not in slot 6; A and B do not occupy adjacent slots; exactly one of these statements is true: E is before F; E is before D. How many distinct arrangements satisfy every rule? Return the count as an integer.

**Oracle answer:** 20

## core-depth/constraints/v001/L1

Arrange A,B,C,D,E,F into slots 1 through 6, each used exactly once. Before means a smaller slot number. Rules: A is before E; F is before E; A is before C. How many distinct arrangements satisfy every rule? Return the count as an integer.

**Oracle answer:** 150

## core-depth/constraints/v001/L2

Arrange A,B,C,D,E,F into slots 1 through 6, each used exactly once. Before means a smaller slot number. Rules: A is before E; F is before E; A is before C; B and F occupy adjacent slots. How many distinct arrangements satisfy every rule? Return the count as an integer.

**Oracle answer:** 50

## core-depth/constraints/v001/L3

Arrange A,B,C,D,E,F into slots 1 through 6, each used exactly once. Before means a smaller slot number. Rules: A is before E; F is before E; A is before C; B and F occupy adjacent slots; D is not in slot 4; A and F do not occupy adjacent slots. How many distinct arrangements satisfy every rule? Return the count as an integer.

**Oracle answer:** 30

## core-depth/constraints/v001/L4

Arrange A,B,C,D,E,F into slots 1 through 6, each used exactly once. Before means a smaller slot number. Rules: A is before E; F is before E; A is before C; B and F occupy adjacent slots; D is not in slot 4; A and F do not occupy adjacent slots; exactly one of these statements is true: F is before C; F is before E. How many distinct arrangements satisfy every rule? Return the count as an integer.

**Oracle answer:** 10
