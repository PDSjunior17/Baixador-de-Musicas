#include <iostream>
#include <string>
#include <vector>
#include <filesystem>
#include <SFML/Audio.hpp>
#include <cstdlib>
#include <ctime>
#include <fstream>
#include <termios.h>
#include <unistd.h>

namespace fs = std::filesystem;

class MusicPlayer {
private:
    std::vector<std::string> playlist;
    sf::Music music;
    int currentTrack;
    bool loop;
    bool shuffle;
    float volume;

public:
    MusicPlayer() : currentTrack(-1), loop(false), shuffle(false), volume(50.0f) {
        loadTracksFromDirectory(".");
        loadLastTrack();
    }

    void loadTracksFromDirectory(const std::string& directory) {
        for (const auto& entry : fs::directory_iterator(directory)) {
            if (entry.path().extension() == ".mp3") {
                playlist.push_back(entry.path().string());
            }
        }
    }

    void listTracks() {
        std::cout << "Available tracks:" << std::endl;
        for (size_t i = 0; i < playlist.size(); ++i) {
            std::cout << i + 1 << ". " << playlist[i] << std::endl;
        }
    }

    void play(int trackIndex) {
        if (trackIndex < 0 || trackIndex >= playlist.size()) {
            std::cout << "Invalid track index!" << std::endl;
            return;
        }
        if (!music.openFromFile(playlist[trackIndex])) {
            std::cout << "Error loading track!" << std::endl;
            return;
        }
        currentTrack = trackIndex;
        saveLastTrack();
        music.setVolume(volume);
        music.play();
        std::cout << "Playing: " << playlist[trackIndex] << std::endl;
    }

    void pause() {
        if (music.getStatus() == sf::Music::Playing) {
            music.pause();
            std::cout << "Music paused." << std::endl;
        }
    }

    void resume() {
        if (music.getStatus() == sf::Music::Paused) {
            music.play();
            std::cout << "Resuming music." << std::endl;
        }
    }

    void stop() {
        music.stop();
        std::cout << "Music stopped." << std::endl;
    }

    void next() {
        if (shuffle) {
            currentTrack = rand() % playlist.size();
        } else {
            currentTrack = (currentTrack + 1) % playlist.size();
        }
        play(currentTrack);
    }

    void previous() {
        currentTrack = (currentTrack - 1 + playlist.size()) % playlist.size();
        play(currentTrack);
    }

    void toggleLoop() {
        loop = !loop;
        std::cout << "Loop mode: " << (loop ? "ON" : "OFF") << std::endl;
    }

    void toggleShuffle() {
        shuffle = !shuffle;
        std::cout << "Shuffle mode: " << (shuffle ? "ON" : "OFF") << std::endl;
    }

    void setVolume(float newVolume) {
        volume = newVolume;
        music.setVolume(volume);
        std::cout << "Volume set to: " << volume << "%" << std::endl;
    }

    float getVolume() const {
        return volume;
    }

    void saveLastTrack() {
        std::ofstream file("last_track.txt");
        file << currentTrack;
        file.close();
    }

    void loadLastTrack() {
        std::ifstream file("last_track.txt");
        if (file) {
            file >> currentTrack;
        }
        file.close();
    }
};

char getKeyPress() {
    struct termios oldt, newt;
    char ch;
    tcgetattr(STDIN_FILENO, &oldt);
    newt = oldt;
    newt.c_lflag &= ~(ICANON | ECHO);
    tcsetattr(STDIN_FILENO, TCSANOW, &newt);
    ch = getchar();
    tcsetattr(STDIN_FILENO, TCSANOW, &oldt);
    return ch;
}

int main() {
    srand(time(0));
    MusicPlayer player;
    player.listTracks();
    
    std::cout << "Use the following keys for control:\n";
    std::cout << "P - Pause\nR - Resume\nN - Next\nB - Previous\nL - Toggle Loop\nS - Toggle Shuffle\n+ - Increase Volume\n- - Decrease Volume\nQ - Quit\n";
    
    char command;
    while (true) {
        command = getKeyPress();
        switch (command) {
            case 'P': case 'p':
                player.pause();
                break;
            case 'R': case 'r':
                player.resume();
                break;
            case 'N': case 'n':
                player.next();
                break;
            case 'B': case 'b':
                player.previous();
                break;
            case 'L': case 'l':
                player.toggleLoop();
                break;
            case 'S': case 's':
                player.toggleShuffle();
                break;
            case '+':
                player.setVolume(player.getVolume() + 10);
                break;
            case '-':
                player.setVolume(player.getVolume() - 10);
                break;
            case 'Q': case 'q':
                return 0;
            default:
                std::cout << "Invalid key!" << std::endl;
        }
    }
}

