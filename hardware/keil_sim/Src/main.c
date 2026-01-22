/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "usart.h"
#include "gpio.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <stdio.h>
#include <string.h>
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */
/* 按照协议定义的碳排放数据结构体 */
typedef struct __attribute__((packed)){
    uint8_t header;     // 0xAA
    uint8_t device_id;  // 0x01
    float power_val;    // 模拟用电量
    float water_val;    // 模拟用水量
    uint8_t checksum;   // 校验位
    uint8_t tail;       // 0x55
} CarbonPacket_t; // 总共12字节
/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/

/* USER CODE BEGIN PV */
uint8_t aRxBuffer[5]; // 接收树莓派发送的 5 字节请求帧 [0xAA, 0x01, ID_L, ID_H, 0x55]
/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */
void Send_Eco_Data(void) {
    char msg[64];
    float power_val, water_val;

    // 模拟动态数据：基础值 + 随机扰动
    // 这里的逻辑保持不变，用于模拟实时变化
    power_val = 2.5f + (float)(HAL_GetTick() % 100) / 50.0f; 
    water_val = 0.5f + (float)(HAL_GetTick() % 200) / 1000.0f;

    // 关键改动：将数据格式化为字符串，方便树莓派 Python 端的 split(':') 解析
    // 增加 \n 作为帧结束标志，树莓派端 readline() 才能正常工作
    int len = sprintf(msg, "elec:%.2f,water:%.3f\n", power_val, water_val);

    // 通过 USART1 发送字符串
    extern UART_HandleTypeDef huart1;
    HAL_UART_Transmit(&huart1, (uint8_t *)msg, len, 100);
}
/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{
  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_USART1_UART_Init();
  /* USER CODE BEGIN 2 */
  // 开启中断接收，监听来自树莓派的请求
  HAL_UART_Receive_IT(&huart1, aRxBuffer, 5);
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
	// Send_Eco_Data();
	// HAL_Delay(1000);
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLMUL = RCC_PLL_MUL9;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
  {
    Error_Handler();
  }
}

/* USER CODE BEGIN 4 */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if(huart->Instance == USART1)
    {
        // 1. 校验请求帧头(0xAA)和指令(0x01)
        if(aRxBuffer[0] == 0xAA && aRxBuffer[1] == 0x01)
        {
            // 2. 准备仿真数据 (实际项目中这里改为读取 ADC 传感器值)
            // 我们让数据随时间微量波动，这样网页上就能看到动效了
            static uint16_t base_elec = 420;   // 模拟 4.20 kWh
            static uint16_t base_water = 115;  // 模拟 1.15 L
            
            base_elec += (HAL_GetTick() % 5);  // 模拟用电波动
            base_water += (HAL_GetTick() % 3); // 模拟用水波动

            // 3. 构造响应帧 [0xBB, 电量L, 电量H, 水量L, 水量H, 0x55]
            uint8_t aTxBuffer[6];
            aTxBuffer[0] = 0xBB;
            aTxBuffer[1] = base_elec & 0xFF;
            aTxBuffer[2] = base_elec >> 8;
            aTxBuffer[3] = base_water & 0xFF;
            aTxBuffer[4] = base_water >> 8;
            aTxBuffer[5] = 0x55;

            // 4. 发送响应给树莓派
            HAL_UART_Transmit(&huart1, aTxBuffer, 6, 100);
        }

        // 5. 必须重新开启中断，否则只能接收一次
        HAL_UART_Receive_IT(&huart1, aRxBuffer, 5);
    }
}
/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}

#ifdef  USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
