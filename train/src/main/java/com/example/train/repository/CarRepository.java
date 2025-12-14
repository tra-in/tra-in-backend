package com.example.train.repository;

import com.example.train.domain.Car;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface CarRepository extends JpaRepository<Car, Long> {
    List<Car> findByTrainIdOrderByCarNo(Long trainId);
}
