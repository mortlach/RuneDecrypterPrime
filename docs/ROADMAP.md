# Active roadmap

This page is the short list of work that remains genuinely active. Release
history and closed contract decisions belong elsewhere.

## Before V1 release

- Run the normal push/pull-request gate on Windows and Ubuntu, including the
  `RELEASE` runnable group.
- Run the manual `full_v1` proof, including complete pytest, package evidence
  and the bounded `FULL_ASSET_EXAMPLES` group.
- Record the final integration head and regenerate the review pack from that
  exact head.
- Keep local folder READMEs aligned when components or useful options change;
  the reader-experience pass establishes the current coverage.

The `QUALIFICATION` group is not part of these checks.

## P7/C7 follow-up

The repository already contains the qualified staged tool and evidence under:

```text
cipher_development/periodic_columnar_staged/
```

No new cipher development or long campaign is authorised by the documentation
migration. The next work item is to define the campaign before running it:

1. select the next scientific question;
2. state which existing evidence makes that question worth testing;
3. choose a bounded compute budget and stop rule;
4. define success, useful partial evidence and failure before looking at the
   result;
5. identify the exact existing tool entry point and output location;
6. review the plan explicitly, then run only the approved bound.

The unresolved item is the scientific question itself. It must not be guessed
from the existence of a warm start or turned into an automatic release task.

## Not active V1 work

- repository-wide style cleanup;
- new public cipher, solver or scorer families;
- unreviewed expansion of the getting-started route;
- routine CI execution of long P7/C7 campaigns.
