window.AGENTIC_TASK_CATALOG = {
  "rerun-teardown": {
    "testFiles": [],
    "testCommand": "",
    "localPath": ""
  },
  "rich-alignment": {
    "testFiles": [],
    "testCommand": "",
    "localPath": ""
  },
  "no-color": {
    "testFiles": ["tests/test_no_color_app.py"],
    "testCommand": "python3 -m unittest discover -s tests -v",
    "localPath": "fixtures/no_color_repo"
  },
  "negative-flag-fixture": {
    "testFiles": ["tests/test_negative_flag_app.py"],
    "testCommand": "python3 -m unittest discover -s tests -p test_negative_flag_app.py -v",
    "localPath": "fixtures/negative_flag_repo"
  },
  "plugin-loader-fixture": {
    "testFiles": ["tests/test_plugin_loader.py"],
    "testCommand": "python3 -m unittest discover -s tests -p test_plugin_loader.py -v",
    "localPath": "fixtures/plugin_loader_repo"
  },
  "click-no-color-real": {
    "testFiles": ["tests/test_issue_no_color.py"],
    "testCommand": "python3 -m unittest discover -s tests -p test_issue_no_color.py -v",
    "localPath": ""
  },
  "click-negative-flag-real": {
    "testFiles": ["tests/test_issue_negative_flag.py"],
    "testCommand": "python3 -m unittest discover -s tests -p test_issue_negative_flag.py -v",
    "localPath": ""
  },
  "click-class-flag-default-real": {
    "testFiles": ["tests/test_issue_class_flag_default.py"],
    "testCommand": "python3 -m unittest discover -s tests -p test_issue_class_flag_default.py -v",
    "localPath": ""
  },
  "markitdown-docx-equations-real": {
    "testFiles": ["tests/test_issue_docx_equations.py"],
    "testCommand": "python3 -m pytest tests/test_issue_docx_equations.py -q",
    "localPath": ""
  },
  "semantic-kernel-plugin-init-real": {
    "testFiles": ["tests/test_issue_kernel_plugin.py"],
    "testCommand": "python3 -m unittest discover -s tests -p test_issue_kernel_plugin.py -v",
    "localPath": ""
  }
};
