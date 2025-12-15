package com.example.train.domain;

import java.util.Locale;

public enum TravelPreference {
    RELAXATION("힐링", "relaxation"),
    ACTIVITY("액티비티", "activity"),
    FOOD("맛집", "food"),
    SHOPPING("쇼핑", "shopping"),
    NATURE("자연", "nature"),
    CULTURE("문화", "culture");

    private final String ko;
    private final String key; // ✅ 추천 API에서 쓰는 영문 키

    TravelPreference(String ko, String key) {
        this.ko = ko;
        this.key = key;
    }

    public String getKo() { return ko; }
    public String getKey() { return key; }

    /** ✅ 한글/ENUM이름/영문키 전부 허용 */
    public static TravelPreference from(String value) {
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalArgumentException("travelPreference is blank");
        }

        String v = value.trim();
        String lower = v.toLowerCase(Locale.ROOT);

        // 1) enum 이름: RELAXATION / FOOD ...
        for (TravelPreference tp : values()) {
            if (tp.name().equalsIgnoreCase(v)) return tp;
        }

        // 2) 영문 키: relaxation / food ...
        for (TravelPreference tp : values()) {
            if (tp.key.equalsIgnoreCase(lower)) return tp;
        }

        // 3) 한글 라벨: 힐링 / 맛집 ...
        for (TravelPreference tp : values()) {
            if (tp.ko.equals(v)) return tp;
        }

        throw new IllegalArgumentException("유효하지 않은 travelPreference 입니다: " + value);
    }
}
