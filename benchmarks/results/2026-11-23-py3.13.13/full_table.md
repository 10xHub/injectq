| Scenario (µs/op, median; × = relative to hand-written) | injectq | aioinject | dependency-injector | dishka | diwire | inject | injector | kink | lagom | punq | rodi | svcs | that-depends | wireup | hand-written |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 cached singleton | 0.083 (4.3x) | 0.295 (15x) | **0.057** (2.9x) | 0.307 (16x) | 0.424 (22x) | 0.158 (8.2x) | 1.331 (69x) | 0.168 (8.7x) | 0.155 (8.0x) | 1.097 (57x) | 0.290 (15x) | 0.189 (9.8x) | 0.077 (4.0x) | 0.092 (4.8x) | 0.019 |
| S2 transient chain (3 deep) | **0.302** (1.8x) | 0.787 (4.7x) | 1.203 (7.3x) | 0.516 (3.1x) | 0.609 (3.7x) | 4.785 (29x) | 42.7 (258x) | 3.688 (22x) | 5.624 (34x) | 36.5 (220x) | 0.758 (4.6x) | 2.590 (16x) | 0.938 (5.7x) | 0.512 (3.1x) | 0.166 |
| S3 wide graph (5 transients, 5 singletons) | **0.550** (1.5x) | 1.768 (5.0x) | 3.038 (8.6x) | 1.069 (3.0x) | 0.884 (2.5x) | 12.2 (34x) | 90.6 (255x) | 12.6 (35x) | 12.0 (34x) | 90.6 (255x) | 1.852 (5.2x) | 8.087 (23x) | 3.479 (9.8x) | 1.434 (4.0x) | 0.355 |
| S4 request scope: enter, resolve, exit | 0.968 (2.8x) | 2.278 (6.6x) | n/a [1] | 1.526 (4.4x) | 4.609 (13x) | n/a [2] | 14.4 (42x) | n/a [2] | n/a [2] | n/a [3] | **0.836** (2.4x) | 1.940 (5.6x) | 24.7 (72x) | 1.130 (3.3x) | 0.345 |
| S5 injected function call (3 deps) | **0.143** (3.5x) | n/a [4] | 1.127 (27x) | 1.165 (28x) | 6.820 (166x) | 2.462 (60x) | 16.8 (409x) | 2.366 (58x) | 1.474 (36x) | n/a [5] | 1.056 (26x) | n/a [6] | 3.163 (77x) | 0.269 (6.5x) | 0.041 |
| S6 async transient chain | **0.427** (1.9x) | 0.992 (4.3x) | 37.8 (165x) | 1.068 (4.7x) | 0.874 (3.8x) | n/a [7] | n/a [8] | n/a [7] | n/a [7] | n/a [8] | n/a [9] | 3.068 (13x) | 1.569 (6.8x) | 0.676 (2.9x) | 0.229 |
| S7 build container (50 services) | 27.4 (21x) | 623 (482x) | 295 (228x) | 4,151 (3,212x) | 2,612 (2,021x) | **13.9** (11x) | 72.5 (56x) | 784 (606x) | 54.0 (42x) | 121 (93x) | 585 (452x) | 369 (286x) | 194 (150x) | 9,768 (7,557x) | 1.292 |
| S7r build container + resolve 50-deep chain | 251 (37x) | 1,924 (280x) | 432 (63x) | 8,858 (1,291x) | 45,764 (6,668x) | **98.3** (14x) | 800 (116x) | 897 (131x) | 888 (129x) | 767 (112x) | 589 (86x) | 451 (66x) | 216 (31x) | 9,642 (1,405x) | 6.863 |

Bold: fastest DI library in the row (hand-written excluded).

[1] n/a: no enter/exit request scope (only context-local singletons, a different mechanism).

[2] n/a: no request scope.

[3] n/a: no request scope (only transient and singleton).

[4] n/a: no generic injection decorator (per-framework `inject` only).

[5] n/a: no injection decorator.

[6] n/a: no generic injection decorator (framework integrations only).

[7] n/a: no async resolution.

[8] n/a: no async API.

[9] n/a: no async resolution (sync only).
