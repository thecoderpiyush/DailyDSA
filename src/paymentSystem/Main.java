package paymentSystem;

public class Main {
    public static void main(String[] args) {
        
        PaymentProcessor creditCardProcessor = new CreditCardPaymentProcessor();
        PaymentProcessor upiPaymentProcessor     = new UPIPaymentProcessor();


        creditCardProcessor.pay(100.0);
        UserAccount userAccount = new UserAccount();
        userAccount.deposit(50.0);
        double balance = userAccount.getBalance();
        System.out.println(balance);




    }
}
