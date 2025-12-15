package com.example.train.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class UserPreferenceRequestDto {

    @JsonProperty("userId")
    private Long userId;

    @JsonProperty("ticketId")
    private Long ticketId;

    // ✅ 한글 enum 문자열 그대로: "힐링", "액티비티", "맛집", ...
    @JsonProperty("travelPreference")
    private String travelPreference;
}
