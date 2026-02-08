# Embedded Systems Development Quick Reference

> **Sources**:
> - https://docs.zephyrproject.org/
> - https://www.freertos.org/Documentation/
> - https://developer.arm.com/documentation
> **Extracted**: 2025-12-21
> **Refresh**: Annually

## RTOS Comparison

| Feature | FreeRTOS | Zephyr | RIOT | NuttX |
|---------|----------|--------|------|-------|
| License | MIT | Apache 2.0 | LGPL 2.1 | Apache 2.0 |
| Min RAM | ~4KB | ~8KB | ~1.5KB | ~32KB |
| Min Flash | ~5KB | ~50KB | ~5KB | ~32KB |
| Scheduler | Priority + Round-robin | Priority + Deadline | Priority + Round-robin | Priority |
| POSIX | Partial | Partial | Partial | Full |
| Security | AWS IoT | PSA, TF-M | DTLS | Varies |

## Memory Management Patterns

### Stack Sizing Rules of Thumb
```c
// Minimum stack sizes (architecture-dependent)
// ARM Cortex-M: 128 bytes minimum (idle task)
// Typical task: 256-512 bytes
// Task with printf: 1024+ bytes
// Network task: 2048+ bytes

#define TASK_STACK_SIZE_MINIMAL   128
#define TASK_STACK_SIZE_DEFAULT   512
#define TASK_STACK_SIZE_NETWORK   2048
```

### Static vs Dynamic Allocation
```c
// Prefer static allocation in safety-critical systems
static StaticTask_t xTaskBuffer;
static StackType_t xStack[STACK_SIZE];

TaskHandle_t xHandle = xTaskCreateStatic(
    vTaskCode,
    "TaskName",
    STACK_SIZE,
    NULL,
    tskIDLE_PRIORITY + 1,
    xStack,
    &xTaskBuffer
);
```

## Interrupt Handling Best Practices

### ISR Guidelines
1. Keep ISRs short (< 10μs ideal)
2. No blocking calls in ISRs
3. Use deferred processing (task notification, queue)
4. Disable only necessary interrupts

```c
// FreeRTOS ISR to task communication
void UART_IRQHandler(void) {
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;

    // Minimal processing in ISR
    uint8_t data = UART_ReadByte();

    // Defer to task
    xQueueSendFromISR(xQueue, &data, &xHigherPriorityTaskWoken);

    // Yield if higher priority task woken
    portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
}
```

## Power Management

### Low-Power Modes (ARM Cortex-M)

| Mode | Wake Sources | Typical Current |
|------|--------------|-----------------|
| Sleep | Any interrupt | 1-10 mA |
| Stop | EXTI, RTC | 1-100 μA |
| Standby | WKUP pin, RTC | 1-10 μA |
| Shutdown | WKUP pin | < 1 μA |

### Power Optimization Checklist
- [ ] Disable unused peripherals
- [ ] Use lowest clock frequency acceptable
- [ ] Configure unused GPIO as analog input
- [ ] Use DMA instead of polling
- [ ] Implement tickless idle mode

## Communication Protocols

### I2C Quick Reference
```
Speed Modes:
- Standard:  100 kHz
- Fast:      400 kHz
- Fast Plus: 1 MHz
- High:      3.4 MHz

Address Format: 7-bit (standard) or 10-bit
Pull-up: 2.2kΩ - 10kΩ (depends on capacitance)
```

### SPI Quick Reference
```
Modes (CPOL, CPHA):
- Mode 0 (0,0): Clock idle low, sample on rising edge
- Mode 1 (0,1): Clock idle low, sample on falling edge
- Mode 2 (1,0): Clock idle high, sample on falling edge
- Mode 3 (1,1): Clock idle high, sample on rising edge

Max Speed: Typically 10-50 MHz (device dependent)
```

### UART Quick Reference
```
Common Baud Rates: 9600, 115200, 921600
Frame: Start bit + 8 data bits + (parity) + stop bit(s)
Flow Control: None, RTS/CTS (hardware), XON/XOFF (software)
```

## Safety-Critical Development

### MISRA C Key Rules (Subset)
- Rule 1.3: No undefined/unspecified behavior
- Rule 2.2: No dead code
- Rule 8.13: Pointer to const where applicable
- Rule 10.4: Use same essential type in operations
- Rule 11.3: No cast between pointer and integral types
- Rule 14.3: No invariant boolean conditions
- Rule 17.7: Return values shall not be discarded

### Defensive Programming
```c
// Always check pointers
if (ptr == NULL) {
    return ERROR_NULL_POINTER;
}

// Bounds checking
if (index >= ARRAY_SIZE) {
    return ERROR_OUT_OF_BOUNDS;
}

// Assert for development
configASSERT(condition);

// Watchdog for runtime
WDG_Refresh();
```

## Debugging Techniques

### Common Debug Interfaces
| Interface | Speed | Pins | Features |
|-----------|-------|------|----------|
| SWD | 4 MHz | 2 | Debug, trace |
| JTAG | 10 MHz | 4-5 | Debug, boundary scan |
| SWO | 2 MHz | 1 | Printf, ITM trace |

### Memory Analysis
```bash
# Check memory usage (arm-none-eabi-gcc)
arm-none-eabi-size firmware.elf

# Generate map file
arm-none-eabi-gcc -Wl,-Map=output.map

# Analyze sections
arm-none-eabi-objdump -h firmware.elf
```

---
*This excerpt was curated for agent knowledge grounding.*
