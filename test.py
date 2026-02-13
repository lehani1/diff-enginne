from schema_detector import detect_schema_changes, compare_yaml_files

result = detect_schema_changes(
    old_config="sd.yml",
    new_config = "sd_new.yml",
    output_format="text"
)
print(result)
# for k in result:
#     print(k, result[k], sep = "\n")