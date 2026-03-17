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
    "description": "The app should disable ANSI color output when the NO_COLOR environment variable is set.",
    "testFiles": ["tests/test_no_color_app.py"],
    "testCommand": "python3 -m unittest discover -s tests -v",
    "localPath": "fixtures/no_color_repo"
  },
  "negative-flag-fixture": {
    "description": "Omitting the negative flag should keep the default True value, while explicitly passing it should flip the value to False.",
    "testFiles": ["tests/test_negative_flag_app.py"],
    "testCommand": "python3 -m unittest discover -s tests -p test_negative_flag_app.py -v",
    "localPath": "fixtures/negative_flag_repo"
  },
  "plugin-loader-fixture": {
    "description": "The plugin loader should skip classes that have no kernel-decorated methods and load the first valid plugin class instead.",
    "testFiles": ["tests/test_plugin_loader.py"],
    "testCommand": "python3 -m unittest discover -s tests -p test_plugin_loader.py -v",
    "localPath": "fixtures/plugin_loader_repo"
  },
  "tag-parser-fixture": {
    "description": "The parser should trim whitespace around comma-separated tags and ignore blank entries.",
    "testFiles": ["tests/test_tag_parser.py"],
    "testCommand": "python3 -m unittest discover -s tests -p test_tag_parser.py -v",
    "localPath": "fixtures/tag_parser_repo"
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
