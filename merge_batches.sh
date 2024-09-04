#!/bin/sh

export $(xargs <.env)

mv ${PDF_PATH}/DocFiles_*/* ${PDF_PATH}
rm -rf ${PDF_PATH}/DocFiles_*

mv ${TEI_PATH}/${MODE}/DocFiles_*/* ${TEI_PATH}/${MODE}
rm -rf ${TEI_PATH}/${MODE}/DocFiles_*

mv ${JSON_PATH}/${MODE}/DocFiles_*/* ${JSON_PATH}/${MODE}
rm -rf ${JSON_PATH}/${MODE}/DocFiles_*
