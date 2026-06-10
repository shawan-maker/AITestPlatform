#!/usr/bin/env python3
"""添加 case_category 相关的 i18n 翻译"""
import json

def update_i18n():
    # 更新 zh-CN.json
    with open('frontend/src/i18n/zh-CN.json', 'r', encoding='utf-8') as f:
        zh_data = json.load(f)
    
    # 添加翻译到 page.functional
    zh_data['page']['functional']['caseCategory'] = '用例分类'
    zh_data['page']['functional']['catFunctional'] = '功能'
    zh_data['page']['functional']['catPerformance'] = '性能'
    zh_data['page']['functional']['catSecurity'] = '安全'
    zh_data['page']['functional']['catCompatibility'] = '兼容性'
    zh_data['page']['functional']['catUsability'] = '易用性'
    zh_data['page']['functional']['catOther'] = '其他'
    
    with open('frontend/src/i18n/zh-CN.json', 'w', encoding='utf-8') as f:
        json.dump(zh_data, f, ensure_ascii=False, indent=2)
    
    print("[OK] Updated zh-CN.json")
    
    # 更新 en-US.json
    with open('frontend/src/i18n/en-US.json', 'r', encoding='utf-8') as f:
        en_data = json.load(f)
    
    # 添加英文翻译到 page.functional
    en_data['page']['functional']['caseCategory'] = 'Case Category'
    en_data['page']['functional']['catFunctional'] = 'Functional'
    en_data['page']['functional']['catPerformance'] = 'Performance'
    en_data['page']['functional']['catSecurity'] = 'Security'
    en_data['page']['functional']['catCompatibility'] = 'Compatibility'
    en_data['page']['functional']['catUsability'] = 'Usability'
    en_data['page']['functional']['catOther'] = 'Other'
    
    with open('frontend/src/i18n/en-US.json', 'w', encoding='utf-8') as f:
        json.dump(en_data, f, ensure_ascii=False, indent=2)
    
    print("[OK] Updated en-US.json")

if __name__ == '__main__':
    update_i18n()
