package com.example.train.dto;

import lombok.Data;
import java.util.List;

@Data
public class UserPickRefreshRequest {

    private Long userId;
    private Long userTicketId;
    private String destStation;

    private List<Long> removeContentIds; // ❌ 제거 + 제외
    private List<Long> keepContentIds;   // ❤️ 유지
}
