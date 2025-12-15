package com.example.train.domain;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

@Entity
@Table(
        name = "user_preference",
        uniqueConstraints = {
                @UniqueConstraint(
                        name = "uk_user_ticket_preference",
                        columnNames = {"user_id", "ticket_id"}
                )
        }
)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UserPreference {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    // ✅ 추가
    @Column(name = "ticket_id", nullable = false)
    private Long ticketId;

    // ✅ 한글 ENUM 그대로
    @Enumerated(EnumType.STRING)
    @Column(name = "travel_preference", nullable = false)
    private TravelPreference travelPreference;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    @PrePersist
    public void onCreate() {
        this.updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    public void onUpdate() {
        this.updatedAt = LocalDateTime.now();
    }
}
